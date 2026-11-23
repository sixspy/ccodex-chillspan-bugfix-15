export const stubsViewTemplate = `
<section class="panel">
  <h2>空桩台</h2>
  <p class="hint">甲轨：承运商导入与解冻事件仅登记任务表，封批正式字段零改；同批提交串行占任务锁，后到只记争用。</p>
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
  <h3>批次封批态(同源，空桩不改)</h3>
  <table class="data-table">
    <thead><tr><th>批次</th><th>同源态</th><th>封批</th><th>桩待办</th><th>已晋升</th><th>一致</th></tr></thead>
    <tbody>
      <tr v-for="s in states" :key="s.batch_id">
        <td>{{ s.batch_code }}</td>
        <td><span class="badge" :class="statusClass(s.status)">{{ s.status }}</span></td>
        <td>{{ s.sealed ? "是" : "否" }}</td>
        <td>{{ s.thaw_pending }}</td>
        <td>{{ s.promoted_progress }}</td>
        <td>{{ s.consistent ? "同源" : "偏航" }}</td>
      </tr>
    </tbody>
  </table>
  <p class="hint">同源一致 {{ stateSummary.consistent || 0 }}/{{ stateSummary.total || 0 }}</p>
</section>
`;
