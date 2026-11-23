export const stubsViewTemplate = `
<section class="panel">
  <h2>空桩台</h2>
  <p class="hint">承运商导入与解冻事件仅登记任务表（埋雷：解冻可能误改封批态）。</p>
  <div class="grid-2">
    <div>
      <h3>承运商导入空桩</h3>
      <div class="form-row">
        <div><label>承运商</label><input v-model="carrierForm.carrier_name"/></div>
        <div><label>行数</label><input type="number" v-model.number="carrierForm.row_count"/></div>
      </div>
      <button @click="doCarrierStub">登记空桩</button>
      <ul><li v-for="j in carrierJobs" :key="j.id">{{ j.carrier_name }} {{ j.row_count }}行 · {{ j.status }}</li></ul>
    </div>
    <div>
      <h3>解冻事件空桩</h3>
      <div class="form-row">
        <div><label>批次ID(可空)</label><input type="number" v-model.number="thawForm.batch_id"/></div>
        <div><label>分钟</label><input type="number" v-model.number="thawForm.thaw_minutes"/></div>
      </div>
      <button @click="doThawStub">登记解冻</button>
      <ul><li v-for="j in thawJobs" :key="j.id">批次 {{ j.batch_id }} {{ j.thaw_minutes }}分 · {{ j.status }}</li></ul>
    </div>
  </div>
</section>
`;