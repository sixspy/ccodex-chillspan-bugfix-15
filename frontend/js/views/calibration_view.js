export const calibrationViewTemplate = `
<section class="panel">
  <h2>探头校准</h2>
  <div class="form-row">
    <div><label>探头</label>
      <select v-model.number="calForm.probe_id"><option v-for="p in probes" :key="p.id" :value="p.id">{{ p.probe_code }}</option></select>
    </div>
    <div><label>偏移(摄氏)</label><input type="number" step="0.1" v-model.number="calForm.offset_c"/></div>
    <div><label>有效至</label><input type="date" v-model="calForm.valid_until"/></div>
    <div><label>质检员</label><input v-model="calForm.officer"/></div>
  </div>
  <div class="actions"><button @click="addCalibration">写入校准</button></div>
  <table class="data-table">
    <thead><tr><th>探头</th><th>校准时间</th><th>偏移</th><th>有效至</th><th>状态</th></tr></thead>
    <tbody>
      <tr v-for="c in calibrations" :key="c.id">
        <td>{{ c.probe_code }}</td>
        <td>{{ c.calibrated_at }}</td>
        <td>{{ c.offset_c }}</td>
        <td>{{ c.valid_until }}</td>
        <td>{{ c.status }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;