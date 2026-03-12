Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 目标时间（ISO字符串或时间戳） */
    targetTime: {
      type: String,
      value: '',
    },
    /** 样式模式：card=卡片式, inline=行内式, seckill=秒杀式 */
    mode: {
      type: String,
      value: 'inline',
    },
    /** 前缀文字 */
    prefix: {
      type: String,
      value: '',
    },
    /** 是否显示天数 */
    showDays: {
      type: Boolean,
      value: true,
    },
  },

  data: {
    days: '00',
    hours: '00',
    minutes: '00',
    seconds: '00',
    isFinished: false,
    totalSeconds: 0,
  },

  lifetimes: {
    attached() {
      this.startCountdown();
    },
    detached() {
      this.stopCountdown();
    },
  },

  observers: {
    targetTime() {
      this.startCountdown();
    },
  },

  methods: {
    _timer: null as number | null,

    startCountdown() {
      this.stopCountdown();
      this.updateTime();
      this._timer = setInterval(() => {
        this.updateTime();
      }, 1000) as unknown as number;
    },

    stopCountdown() {
      if (this._timer) {
        clearInterval(this._timer);
        this._timer = null;
      }
    },

    updateTime() {
      const { targetTime } = this.data;
      if (!targetTime) return;

      const target = new Date(targetTime).getTime();
      const now = Date.now();
      let diff = Math.max(0, Math.floor((target - now) / 1000));

      if (diff <= 0) {
        this.setData({
          days: '00',
          hours: '00',
          minutes: '00',
          seconds: '00',
          isFinished: true,
          totalSeconds: 0,
        });
        this.stopCountdown();
        this.triggerEvent('finish');
        return;
      }

      const days = Math.floor(diff / 86400);
      diff %= 86400;
      const hours = Math.floor(diff / 3600);
      diff %= 3600;
      const minutes = Math.floor(diff / 60);
      const seconds = diff % 60;

      this.setData({
        days: String(days).padStart(2, '0'),
        hours: String(hours).padStart(2, '0'),
        minutes: String(minutes).padStart(2, '0'),
        seconds: String(seconds).padStart(2, '0'),
        isFinished: false,
        totalSeconds: diff,
      });
    },
  },
});
