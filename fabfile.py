"""
一月一露 Fabric / Podman 运维任务。

流程参考 ~/projects/apigateway/Fy-api:
    本地推代码
      -> 服务器拉取/检出
      -> 服务器 podman build
      -> 可选 push 到镜像仓库
      -> 后续接入 blue-green / systemd 部署脚本

准备:
    pip install -r scripts/ops/requirements.txt

常用命令:
    fab info
    fab preflight
    fab check
    fab status
    fab podman-ps
    fab build --tag=v0.1.0
    fab build-api --tag=v0.1.0
    fab push-image --image=api --tag=v0.1.0
    fab logs --name=yyyl-api --tail=200
    fab health
    fab nginx-test
    fab login-history

默认目标:
    prod: ssh yyyl

可用环境变量覆盖:
    YYYL_TARGET
    YYYL_HOST, YYYL_PORT, YYYL_USER, YYYL_KEY
    YYYL_REPO_URL, YYYL_SRC_DIR, YYYL_BUILD_DIR
    YYYL_REGISTRY, YYYL_NAMESPACE
    YYYL_ENV_FILE, YYYL_NGINX_CONF
    YYYL_PODMAN_RUN_ARGS
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import tempfile
from pathlib import Path

from fabric import Connection, task


TARGETS = {
    "prod": {
        "host": "49.235.185.226",
        "port": 58422,
        "user": "root",
        "key": "~/.ssh/yyyl.pem",
        "app_dir": "/opt/yyyl",
        "src_dir": "/opt/yyyl",
        "build_dir": "/tmp/yyyl-build",
        "registry": "",
        "namespace": "",
        "repo_url": "",
        "nginx_conf": "/www/server/panel/vhost/nginx/ttt.conf",
        "env_file": "/opt/yyyl/server/.env",
        "podman_run_args": "",
        "health_path": "/health",
        "blue_port": 8001,
        "green_port": 8002,
        "container_port": 8000,
        "memory": "1g",
        "cpus": "1",
        "api_repo": "yyyl-api",
        "admin_repo": "yyyl-admin",
        "nginx_repo": "yyyl-nginx",
    },
}

DEFAULT_REF = os.getenv("YYYL_DEFAULT_REF", "origin/main")
DEPLOY_LOCK = os.getenv("YYYL_DEPLOY_LOCK", "/tmp/yyyl-deploy.lock")
SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9._/@:+-]+$")
IMAGE_KEYS = {
    "api": "api_repo",
    "admin": "admin_repo",
    "nginx": "nginx_repo",
}


def _validate_arg(name: str, value: str) -> str:
    if not value:
        raise ValueError(f"{name} is required")
    if not SAFE_ARG_RE.match(value):
        raise ValueError(f"unsafe {name}: {value!r}")
    return value


def _q(value: str) -> str:
    return shlex.quote(value)


def _config(target: str | None = None) -> dict[str, object]:
    name = target or os.getenv("YYYL_TARGET", "prod")
    if name not in TARGETS:
        raise ValueError(f"unknown target {name!r}; expected one of: {', '.join(TARGETS)}")

    cfg = dict(TARGETS[name])
    cfg["name"] = name
    overrides = {
        "host": "YYYL_HOST",
        "port": "YYYL_PORT",
        "user": "YYYL_USER",
        "key": "YYYL_KEY",
        "app_dir": "YYYL_APP_DIR",
        "src_dir": "YYYL_SRC_DIR",
        "build_dir": "YYYL_BUILD_DIR",
        "registry": "YYYL_REGISTRY",
        "namespace": "YYYL_NAMESPACE",
        "repo_url": "YYYL_REPO_URL",
        "nginx_conf": "YYYL_NGINX_CONF",
        "env_file": "YYYL_ENV_FILE",
        "podman_run_args": "YYYL_PODMAN_RUN_ARGS",
        "health_path": "YYYL_HEALTH_PATH",
        "blue_port": "YYYL_BLUE_PORT",
        "green_port": "YYYL_GREEN_PORT",
        "container_port": "YYYL_CONTAINER_PORT",
        "memory": "YYYL_MEM",
        "cpus": "YYYL_CPUS",
        "api_repo": "YYYL_API_REPO",
        "admin_repo": "YYYL_ADMIN_REPO",
        "nginx_repo": "YYYL_NGINX_REPO",
    }
    for key, env_name in overrides.items():
        value = os.getenv(env_name)
        if value:
            cfg[key] = int(value) if key in {"port", "blue_port", "green_port", "container_port"} else value

    cfg["key"] = os.path.expanduser(str(cfg.get("key") or ""))
    return cfg


def _image(cfg: dict[str, object], image: str, tag: str) -> str:
    tag = _validate_arg("tag", tag)
    image = _validate_arg("image", image)
    if image not in IMAGE_KEYS:
        raise ValueError(f"unknown image {image!r}; expected one of: {', '.join(IMAGE_KEYS)}")
    repo = str(cfg[IMAGE_KEYS[image]])
    if cfg.get("registry") and cfg.get("namespace"):
        return f"{cfg['registry']}/{cfg['namespace']}/{repo}:{tag}"
    return f"{repo}:{tag}"


def _connect(cfg: dict[str, object]) -> Connection:
    connect_kwargs = {}
    key = str(cfg.get("key") or "")
    if key:
        connect_kwargs["key_filename"] = key
    return Connection(
        host=str(cfg["host"]),
        user=str(cfg["user"]),
        port=int(cfg["port"]),
        connect_kwargs=connect_kwargs,
    )


def _run(c: Connection, command: str, *, warn: bool = False, hide: bool = False):
    if not hide:
        print(f"[{c.user}@{c.host}:{c.port}] $ {command}")
    return c.run(command, warn=warn, hide=hide, pty=False)


def _ensure_source_checkout(c: Connection, cfg: dict[str, object]):
    repo_url = str(cfg.get("repo_url") or "")
    src_dir = str(cfg["src_dir"])
    src = _q(src_dir)
    if not repo_url:
        _run(c, f"test -d {src}", warn=False)
        return

    parent = _q(str(Path(src_dir).parent))
    repo = _q(repo_url)
    _run(
        c,
        " && ".join(
            [
                f"mkdir -p {parent}",
                f"if [ ! -d {src}/.git ]; then git clone {repo} {src}; fi",
                f"test -d {src}/.git",
            ]
        ),
    )


def _checkout_ref(c: Connection, cfg: dict[str, object], ref: str):
    ref = _validate_arg("ref", ref)
    src = _q(str(cfg["src_dir"]))
    quoted_ref = _q(ref)
    _run(
        c,
        " && ".join(
            [
                f"cd {src}",
                "if [ -d .git ]; then git fetch origin --tags --prune; fi",
                f"if [ -d .git ]; then git checkout -f {quoted_ref}; fi",
                f"if [ -d .git ]; then git reset --hard {quoted_ref}; fi",
                "if [ -d .git ]; then git rev-parse --short HEAD; else echo 'no git checkout; using existing source tree'; fi",
            ]
        ),
    )


def _podman_build(c: Connection, cfg: dict[str, object], image: str, tag: str, dockerfile: str, context: str, flags: list[str]):
    src = _q(str(cfg["src_dir"]))
    image_ref = _q(_image(cfg, image, tag))
    flag_str = " ".join(flags)
    _run(c, f"cd {src} && podman build {flag_str} -t {image_ref} -f {_q(dockerfile)} {_q(context)}")


def _prod_scripts_dir() -> Path:
    return Path(__file__).resolve().parent / "scripts" / "prod"


def _upload_prod_scripts(c: Connection, cfg: dict[str, object]):
    scripts_dir = _prod_scripts_dir()
    if not scripts_dir.is_dir():
        raise FileNotFoundError(f"prod scripts not found: {scripts_dir}")

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "yyyl-prod-scripts.tar.gz"
        subprocess.run(
            ["tar", "-czf", str(archive), "-C", str(scripts_dir.parent), "prod"],
            check=True,
        )
        remote_archive = "/tmp/yyyl-prod-scripts.tar.gz"
        c.put(str(archive), remote_archive)

    app_dir = _q(str(cfg["app_dir"]))
    _run(
        c,
        " && ".join(
            [
                f"mkdir -p {app_dir}/scripts",
                f"rm -rf {app_dir}/scripts/prod",
                f"tar -xzf {_q(remote_archive)} -C {app_dir}/scripts",
                f"chmod +x {app_dir}/scripts/prod/*.sh",
                f"rm -f {_q(remote_archive)}",
            ]
        ),
    )


@task(help={"target": "目标名称，默认 prod"})
def info(ctx, target="prod"):
    """打印本地 Fabric / Podman 目标配置。"""
    cfg = _config(target)
    print(f"target:    {cfg['name']}")
    print(f"host:      {cfg['user']}@{cfg['host']}:{cfg['port']}")
    print(f"key:       {cfg['key']}")
    print(f"app_dir:   {cfg['app_dir']}")
    print(f"src:       {cfg['src_dir']}")
    print(f"build_dir: {cfg['build_dir']}")
    print(f"repo_url:  {cfg.get('repo_url') or '<existing source tree>'}")
    if cfg.get("registry") and cfg.get("namespace"):
        print(f"registry:  {cfg['registry']}/{cfg['namespace']}")
    else:
        print("registry:  <not configured>")
    print(f"api:       {cfg['api_repo']}:<tag>")
    print(f"admin:     {cfg['admin_repo']}:<tag>")
    print(f"nginx:     {cfg['nginx_repo']}:<tag>")
    print(f"env_file:  {cfg['env_file']}")
    print(f"nginx_conf:{cfg['nginx_conf']}")
    print(f"ports:     blue={cfg['blue_port']} green={cfg['green_port']} container={cfg['container_port']}")


@task(help={"target": "目标名称，默认 prod"})
def preflight(ctx, target="prod"):
    """检查 SSH 连通性和服务器基础信息。"""
    cfg = _config(target)
    key = str(cfg.get("key") or "")
    if key and not Path(key).exists():
        raise FileNotFoundError(f"SSH key not found: {key}")

    c = _connect(cfg)
    _run(c, "hostnamectl || uname -a")
    _run(c, "id && pwd && df -h / | awk 'NR==1 || NR==2'")
    _run(c, "command -v dnf || command -v yum || command -v apt-get || true")


@task(help={"target": "目标名称，默认 prod"})
def check(ctx, target="prod"):
    """检查远端 Podman 部署前置条件。"""
    cfg = _config(target)
    key = str(cfg.get("key") or "")
    if key and not Path(key).exists():
        raise FileNotFoundError(f"SSH key not found: {key}")

    c = _connect(cfg)
    _run(c, "command -v git && command -v podman && command -v curl && command -v flock")
    _run(c, "podman info >/dev/null")
    _run(c, f"test -d {_q(str(cfg['app_dir']))}")
    _run(c, f"test -d {_q(str(cfg['src_dir']))}")
    _run(c, f"test -f {_q(str(cfg['env_file']))}", warn=True)
    _run(c, f"test -f {_q(str(cfg['nginx_conf']))}", warn=True)


@task(help={"target": "目标名称，默认 prod"})
def upload_scripts(ctx, target="prod"):
    """上传 scripts/prod 到线上 app_dir/scripts/prod。"""
    cfg = _config(target)
    c = _connect(cfg)
    _upload_prod_scripts(c, cfg)


@task(help={"target": "目标名称，默认 prod"})
def bootstrap_system(ctx, target="prod"):
    """上传 prod 脚本并执行一次性系统初始化。"""
    cfg = _config(target)
    c = _connect(cfg)
    _upload_prod_scripts(c, cfg)
    _run(c, f"APP_DIR={_q(str(cfg['app_dir']))} {_q(str(cfg['app_dir']))}/scripts/prod/01-setup-system.sh")


@task(help={"target": "目标名称，默认 prod", "ref": "远端 Git ref"})
def sync_code(ctx, target="prod", ref=DEFAULT_REF):
    """拉取并检出远端源码；未配置 repo_url 时仅确认源码目录存在。"""
    cfg = _config(target)
    c = _connect(cfg)
    _ensure_source_checkout(c, cfg)
    _checkout_ref(c, cfg, ref)


@task(
    help={
        "target": "目标名称，默认 prod",
        "tag": "镜像标签，例如 v0.1.0",
        "ref": "构建前检出的 Git ref；默认等于 tag",
        "pull": "传递 --pull",
        "no_cache": "传递 --no-cache",
    }
)
def build_api(ctx, target="prod", tag="", ref="", pull=True, no_cache=False):
    """在服务器上用 Podman 构建 FastAPI 镜像。"""
    tag = _validate_arg("tag", tag)
    cfg = _config(target)
    c = _connect(cfg)
    _ensure_source_checkout(c, cfg)
    _checkout_ref(c, cfg, ref or tag)
    flags = ["--pull"] if pull else []
    if no_cache:
        flags.append("--no-cache")
    _podman_build(c, cfg, "api", tag, "server/Dockerfile", "server", flags)


@task(help={"target": "目标名称，默认 prod", "tag": "镜像标签", "pull": "传递 --pull", "no_cache": "传递 --no-cache"})
def build_admin(ctx, target="prod", tag="", pull=True, no_cache=False):
    """在服务器上用 Podman 构建管理后台镜像。"""
    tag = _validate_arg("tag", tag)
    cfg = _config(target)
    c = _connect(cfg)
    _ensure_source_checkout(c, cfg)
    flags = ["--pull"] if pull else []
    if no_cache:
        flags.append("--no-cache")
    _podman_build(c, cfg, "admin", tag, "admin/Dockerfile", "admin", flags)


@task(help={"target": "目标名称，默认 prod", "tag": "镜像标签", "pull": "传递 --pull", "no_cache": "传递 --no-cache"})
def build_nginx(ctx, target="prod", tag="", pull=True, no_cache=False):
    """在服务器上用 Podman 构建 Nginx 网关镜像。"""
    tag = _validate_arg("tag", tag)
    cfg = _config(target)
    c = _connect(cfg)
    _ensure_source_checkout(c, cfg)
    flags = ["--pull"] if pull else []
    if no_cache:
        flags.append("--no-cache")
    _podman_build(c, cfg, "nginx", tag, "nginx/Dockerfile", "nginx", flags)


@task(help={"target": "目标名称，默认 prod", "tag": "镜像标签", "ref": "Git ref", "pull": "传递 --pull"})
def build(ctx, target="prod", tag="", ref="", pull=True):
    """构建 api/admin/nginx 三个镜像。"""
    tag = _validate_arg("tag", tag)
    build_api(ctx, target=target, tag=tag, ref=ref or tag, pull=pull)
    build_admin(ctx, target=target, tag=tag, pull=pull)
    build_nginx(ctx, target=target, tag=tag, pull=pull)


@task(help={"target": "目标名称，默认 prod", "image": "api/admin/nginx", "tag": "镜像标签"})
def push_image(ctx, target="prod", image="api", tag=""):
    """推送单个 Podman 镜像到仓库。"""
    cfg = _config(target)
    if not (cfg.get("registry") and cfg.get("namespace")):
        raise ValueError("registry is not configured; set YYYL_REGISTRY and YYYL_NAMESPACE")
    c = _connect(cfg)
    _run(c, f"podman push {_q(_image(cfg, image, tag))}")


@task(help={"target": "目标名称，默认 prod", "tag": "镜像标签"})
def push_all(ctx, target="prod", tag=""):
    """推送 api/admin/nginx 三个镜像。"""
    tag = _validate_arg("tag", tag)
    for image in IMAGE_KEYS:
        push_image(ctx, target=target, image=image, tag=tag)


@task(help={"target": "目标名称，默认 prod", "tag": "镜像标签", "skip_pull": "使用本地镜像, 不 pull"})
def deploy(ctx, target="prod", tag="", skip_pull=False):
    """调用线上 Podman 蓝绿脚本发布 API。"""
    tag = _validate_arg("tag", tag)
    cfg = _config(target)
    c = _connect(cfg)
    _upload_prod_scripts(c, cfg)

    image = _image(cfg, "api", tag)
    env_parts = [
        f"APP_DIR={_q(str(cfg['app_dir']))}",
        f"IMAGE={_q(image)}",
        f"REPO={_q(str(cfg['api_repo']))}",
        f"ENV_FILE={_q(str(cfg['env_file']))}",
        f"NGINX_CONF={_q(str(cfg['nginx_conf']))}",
        f"HEALTH_PATH={_q(str(cfg['health_path']))}",
        f"BLUE_PORT={int(cfg['blue_port'])}",
        f"GREEN_PORT={int(cfg['green_port'])}",
        f"CONTAINER_PORT={int(cfg['container_port'])}",
        f"MEM={_q(str(cfg['memory']))}",
        f"CPUS={_q(str(cfg['cpus']))}",
    ]
    if cfg.get("podman_run_args"):
        env_parts.append(f"PODMAN_RUN_ARGS={_q(str(cfg['podman_run_args']))}")
    if not (cfg.get("registry") and cfg.get("namespace")) or skip_pull:
        env_parts.append("SKIP_PULL=1")
    deploy_cmd = (
        " ".join(env_parts)
        + f" {_q(str(cfg['app_dir']))}/scripts/prod/06-deploy-blue-green.sh {_q(tag)}"
    )
    _run(c, f"flock {_q(DEPLOY_LOCK)} -c {_q(deploy_cmd)}")


@task(
    help={
        "target": "目标名称，默认 prod",
        "tag": "镜像标签",
        "ref": "Git ref",
        "skip_build": "跳过构建",
        "skip_push": "跳过推送",
    }
)
def release(ctx, target="prod", tag="", ref="", skip_build=False, skip_push=False):
    """构建、可选推送并蓝绿发布 API。"""
    tag = _validate_arg("tag", tag)
    cfg = _config(target)
    has_registry = bool(cfg.get("registry") and cfg.get("namespace"))
    if not skip_build:
        build(ctx, target=target, tag=tag, ref=ref or tag)
    if has_registry and not skip_push:
        push_image(ctx, target=target, image="api", tag=tag)
    deploy(ctx, target=target, tag=tag, skip_pull=not has_registry or skip_push)
    health(ctx, target=target)


@task(help={"target": "目标名称，默认 prod"})
def rollback(ctx, target="prod"):
    """在 yyyl-api-blue/green 之间回滚到另一个已存在容器。"""
    cfg = _config(target)
    c = _connect(cfg)
    nginx_conf = _q(str(cfg["nginx_conf"]))
    blue_port = int(cfg["blue_port"])
    green_port = int(cfg["green_port"])
    rollback_cmd = f"""
set -euo pipefail
if podman ps --format '{{{{.Names}}}}' | grep -qx yyyl-api-blue; then
  CUR=blue; CUR_PORT={blue_port}; NEXT=green; NEXT_PORT={green_port}
elif podman ps --format '{{{{.Names}}}}' | grep -qx yyyl-api-green; then
  CUR=green; CUR_PORT={green_port}; NEXT=blue; NEXT_PORT={blue_port}
else
  echo 'no active yyyl-api-blue/green container' >&2
  exit 1
fi
podman ps -a --format '{{{{.Names}}}}' | grep -qx "yyyl-api-$NEXT"
podman start "yyyl-api-$NEXT"
cp -a {nginx_conf} {nginx_conf}.bak.$(date +%Y%m%d%H%M%S).pre-yyyl-rollback
sed -i -E "/upstream[[:space:]]+yyyl_api_backend[[:space:]]*\\{{/,/\\}}/s|(server[[:space:]]+127\\.0\\.0\\.1:)[0-9]+([[:space:];])|\\1$NEXT_PORT\\2|" {nginx_conf}
nginx -t
systemctl reload nginx || nginx -s reload
podman stop -t 20 "yyyl-api-$CUR" || true
echo "rollback: $CUR -> $NEXT"
"""
    _run(c, f"flock {_q(DEPLOY_LOCK)} -c {_q(rollback_cmd)}")


@task(help={"target": "目标名称，默认 prod"})
def podman_ps(ctx, target="prod"):
    """查看 Podman 容器。"""
    cfg = _config(target)
    c = _connect(cfg)
    _run(c, "podman ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}\\t{{.Ports}}'", warn=True)


@task(help={"target": "目标名称，默认 prod"})
def status(ctx, target="prod"):
    """查看远端源码、Podman、系统服务、端口和磁盘。"""
    cfg = _config(target)
    c = _connect(cfg)
    src = _q(str(cfg["src_dir"]))
    _run(c, f"test -d {src}/.git && cd {src} && git log -1 --oneline || echo 'no git metadata'", warn=True)
    _run(c, "podman ps -a --format 'table {{.Names}}\\t{{.Status}}\\t{{.Image}}' || true", warn=True)
    _run(c, "podman images --format 'table {{.Repository}}\\t{{.Tag}}\\t{{.Size}}\\t{{.CreatedSince}}' | grep -E 'REPOSITORY|yyyl' || true", warn=True)
    _run(c, "systemctl --no-pager --type=service --state=running | grep -E 'podman|docker|nginx|sshd|postgres|redis|site_total|bt' || true", warn=True)
    _run(c, "ss -ltnp", warn=True)
    _run(c, "df -hT / /var/lib/containers /var/lib/docker 2>/dev/null || df -hT /", warn=True)


@task(help={"target": "目标名称，默认 prod"})
def health(ctx, target="prod"):
    """检查本机 Nginx 和后端健康端点。"""
    cfg = _config(target)
    c = _connect(cfg)
    _run(c, "curl -I --max-time 10 http://127.0.0.1 || true", warn=True)
    _run(c, "curl -i --max-time 10 http://127.0.0.1/health || true", warn=True)
    _run(c, "curl -i --max-time 10 http://127.0.0.1/api/v1/products || true", warn=True)


@task(help={"target": "目标名称，默认 prod"})
def nginx_test(ctx, target="prod"):
    """检查远端 Nginx 配置语法。"""
    cfg = _config(target)
    c = _connect(cfg)
    _run(c, "nginx -t")


@task(help={"target": "目标名称，默认 prod", "name": "容器名", "tail": "日志行数"})
def logs(ctx, target="prod", name="yyyl-api", tail=100):
    """查看指定 Podman 容器日志。"""
    name = _validate_arg("name", name)
    tail = int(tail)
    if tail < 1 or tail > 5000:
        raise ValueError("tail must be between 1 and 5000")

    cfg = _config(target)
    c = _connect(cfg)
    _run(c, f"podman logs --tail {tail} {_q(name)}", warn=True)


@task(help={"target": "目标名称，默认 prod"})
def login_history(ctx, target="prod"):
    """查看最近登录记录。"""
    cfg = _config(target)
    c = _connect(cfg)
    _run(c, "who || true", warn=True)
    _run(c, "last -20 || true", warn=True)


@task(help={"target": "目标名称，默认 prod", "tail": "日志行数"})
def ssh_logs(ctx, target="prod", tail=120):
    """查看 sshd 最近日志。"""
    tail = int(tail)
    if tail < 1 or tail > 1000:
        raise ValueError("tail must be between 1 and 1000")

    cfg = _config(target)
    c = _connect(cfg)
    _run(c, f"journalctl -u sshd --since '30 days ago' --no-pager | tail -{tail}", warn=True)
