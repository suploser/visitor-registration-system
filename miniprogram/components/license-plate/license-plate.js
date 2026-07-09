// 多车辆车牌输入组件 - 自定义顺序键盘
const constants = require('../../utils/constants');

// 城市字母（A-Z，排除I和O）
const CITY_LETTERS = [];
for (let i = 65; i <= 90; i++) {
  const l = String.fromCharCode(i);
  if (l !== 'I' && l !== 'O') CITY_LETTERS.push(l);
}

// 号码键盘布局（数字 + 字母 + 退格 + 确认）
const NUM_KEYS = [
  '1','2','3','4','5','6','7','8','9','0',
  'Q','W','E','R','T','Y','U','P',
  'A','S','D','F','G','H','J','K','L',
  'Z','X','C','V','B','N','M',
  '⌫','✓'
];

Component({
  properties: {
    value: { type: Array, value: [] }  // [{value: '京A12345', isNewEnergy: false}]
  },

  data: {
    plates: [],           // 已确认的车牌列表
    kbVisible: false,     // 键盘可见
    kbStep: 0,            // 0=省 1=市 2=号
    kbProvince: '',
    kbCity: '',
    kbNumber: '',
    kbIsNewEnergy: false,
    kbMaxLen: 6,
    provinces: constants.PROVINCES,
    cityLetters: CITY_LETTERS,
    numKeys: NUM_KEYS,
  },

  lifetimes: {
    attached() {
      if (this.properties.value && this.properties.value.length > 0) {
        this.setData({ plates: this.properties.value });
      }
    }
  },

  methods: {
    // 打开键盘
    openKeyboard() {
      this.setData({
        kbVisible: true,
        kbStep: 0,
        kbProvince: '',
        kbCity: '',
        kbNumber: '',
        kbIsNewEnergy: false,
        kbMaxLen: 6,   // 允许最多6位（5位油车 / 6位新能源）
      });
    },

    // 关闭键盘
    kbClose() {
      if (this.data.kbProvince || this.data.kbCity || this.data.kbNumber) {
        wx.showModal({
          title: '确认关闭',
          content: '当前输入的车牌尚未保存，确定关闭吗？',
          success: (res) => {
            if (res.confirm) this.setData({ kbVisible: false });
          }
        });
      } else {
        this.setData({ kbVisible: false });
      }
    },

    // 返回上一步
    kbBack() {
      const step = this.data.kbStep;
      if (step === 0) {
        // 第一步点取消 = 关闭
        this.kbClose();
      } else if (step === 1) {
        this.setData({ kbStep: 0, kbCity: '', kbNumber: '', kbIsNewEnergy: false });
      } else if (step === 2) {
        this.setData({ kbStep: 1, kbNumber: '', kbIsNewEnergy: false });
      }
    },

    // 选择省份
    selectProvince(e) {
      const val = e.currentTarget.dataset.val;
      this.setData({
        kbProvince: val,
        kbStep: 1,
      });
    },

    // 选择城市字母
    selectCity(e) {
      const val = e.currentTarget.dataset.val;
      this.setData({
        kbCity: val,
        kbStep: 2,
        kbIsNewEnergy: false,
        kbMaxLen: 6,      // 允许5位（油车）或6位（新能源）
        kbNumber: '',
      });
    },

    // 输入号码字符
    inputChar(e) {
      const val = e.currentTarget.dataset.val;
      let number = this.data.kbNumber;
      if (number.length >= this.data.kbMaxLen) {
        wx.showToast({ title: `最多输入${this.data.kbMaxLen}位`, icon: 'none', duration: 1000 });
        return;
      }
      number += val;
      // 自动检测新能源：第1位为新能源标识字母（用于预览变色）
      // 或已输入第6位（必然是新能源）
      let isNewEnergy = this.data.kbIsNewEnergy;
      if (!isNewEnergy && number.length === 1 && constants.NEW_ENERGY_LETTERS.includes(number[0])) {
        isNewEnergy = true;
      }
      // 输入第6位时自动切换为新能源
      if (number.length === 6) {
        isNewEnergy = true;
      }
      this.setData({ kbNumber: number, kbIsNewEnergy: isNewEnergy });
    },

    // 退格
    kbBackspace() {
      const number = this.data.kbNumber;
      if (number.length > 0) {
        const newNum = number.slice(0, -1);
        let isNewEnergy = this.data.kbIsNewEnergy;
        // 退格后不足6位 → 恢复为普通车牌（预览变回蓝色）
        if (isNewEnergy && newNum.length < 6) {
          // 仍检查第1位是否为新能源字母
          if (newNum.length >= 1 && constants.NEW_ENERGY_LETTERS.includes(newNum[0])) {
            isNewEnergy = true;
          } else {
            isNewEnergy = false;
          }
        }
        this.setData({ kbNumber: newNum, kbIsNewEnergy: isNewEnergy });
      }
    },

    // 确认当前车牌
    kbConfirm() {
      const { kbProvince, kbCity, kbNumber, plates } = this.data;
      if (!kbProvince || !kbCity || !kbNumber) {
        wx.showToast({ title: '请完成车牌输入', icon: 'none' });
        return;
      }
      // 号码长度必须为5位（油车）或6位（新能源）
      if (kbNumber.length < 5) {
        wx.showToast({ title: `号码至少5位，当前${kbNumber.length}位`, icon: 'none' });
        return;
      }
      if (kbNumber.length > 6) {
        wx.showToast({ title: '号码最多6位', icon: 'none' });
        return;
      }
      // 按长度判断：5位=油车，6位=新能源
      const isNewEnergy = kbNumber.length === 6;
      const fullPlate = kbProvince + kbCity + kbNumber;

      // 检查重复
      if (plates.some(p => p.value === fullPlate)) {
        wx.showToast({ title: '该车牌已添加', icon: 'none' });
        return;
      }

      plates.push({ value: fullPlate, isNewEnergy });
      this.setData({
        plates,
        kbVisible: false,
      });
      this.emitChange();
    },

    // 删除车牌
    deletePlate(e) {
      const index = e.currentTarget.dataset.index;
      const plates = this.data.plates;
      plates.splice(index, 1);
      this.setData({ plates });
      this.emitChange();
    },

    // 通知父组件
    emitChange() {
      this.triggerEvent('change', {
        license_plates: this.data.plates.map(p => p.value),
        plates: this.data.plates,
      });
    },

    noop() {},
  }
});
