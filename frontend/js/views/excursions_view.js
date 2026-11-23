export const excursionsViewTemplate = `
<section class="panel">
  <h2>超温游标</h2>
  <p class="hint">温度点超阈后开游标；须全部闭环才能封批。</p>
  <div class="form-row">
    <div><label>批次</label>
      <select v-model.number="excOpenForm.batch_id"><option v-for="b in openableBatches" :key="b.id" :value="b.id">{{ b.batch_code }}</option></select>
    </div>
    <div><label>自定义阈(可空)</label><input type="number" v-model.number="excOpenForm.threshold" step="0.1"/></div>
    <div><label>备注</label><input v-model="excOpenForm.note"/></div>
  </div>
  <div class="actions">
    <button @click="openExcursion">开游标</button>
    <button class="secondary" @click="closeSelectedExcursion">闭选中游标</button>
  </div>
  <table class="data-table">
    <thead><tr><th>游标键</th><th>批次</th><th>峰值</th><th>阈</th><th>状态</th><th>开时</th></tr></thead>
    <tbody>
      <tr v-for="e in excursions" :key="e.id" @click="selectedExcursion=e" :class="{picked:selectedExcursion&&selectedExcursion.id===e.id}">
        <td>{{ e.cursor_key }}</td>
        <td>{{ e.batch_code }}</td>
        <td>{{ e.peak_temp }}℃</td>
        <td>{{ e.threshold }}℃</td>
        <td><span class="badge" :class="excursionClass(e.status)">{{ e.status }}</span></td>
        <td>{{ e.opened_at }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;