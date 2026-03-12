Page({
  data: {
    userInfo: null as IUserInfo | null,
  },
  onLoad() {
    const app = getApp<IAppOption>();
    this.setData({ userInfo: app.globalData.userInfo });
  },
  onChooseAvatar() {
    wx.chooseMedia({
      count: 1, mediaType: ['image'],
      success: (res) => { console.log('avatar:', res.tempFiles[0].tempFilePath); },
    });
  },
});
