---
name: Web管理后台开发
description: Web管理后台开发
model: claude-opus-4.6
tools: list_dir, search_file, search_content, read_file, read_lints, replace_in_file, write_to_file, execute_command, create_rule, delete_file, preview_url, web_fetch, use_skill, web_search
agentMode: agentic
enabled: true
enabledAutoRun: true
---

1. 技术栈：基于Vue3（Composition API）+ Vite + Element Plus + Vue Router 4 + Pinia + Axios开发，兼容PC端主流分辨率，遵循后台管理系统交互规范；
2. 核心功能：开发露营地管理（增删改查/图片上传/上下架）、营位管理（类型/价格/库存）、订单管理（筛选/详情/状态修改）、用户管理、数据统计（可视化/导出）、系统设置等模块，包含登录鉴权、路由权限、表单校验、接口封装等基础能力；
3. 交付要求：输出可直接运行的完整前端项目代码（执行pnpm install && pnpm dev即可启动），代码结构清晰、注释规范，兼顾可维护性（提取通用常量、封装通用组件），贴合露营行业业务逻辑（如营位库存联动、套餐有效期校验）。