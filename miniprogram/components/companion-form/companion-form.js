// 同行人表单组件
Component({
  properties: {
    index: { type: Number, value: 0 },
    data: { type: Object, value: { name: '', id_number: '' } },
  },
  methods: {
    onNameInput(e) {
      this.triggerEvent('change', {
        index: this.properties.index,
        field: 'name',
        value: e.detail.value,
      });
    },
    onIdInput(e) {
      this.triggerEvent('change', {
        index: this.properties.index,
        field: 'id_number',
        value: e.detail.value,
      });
    },
  }
});
