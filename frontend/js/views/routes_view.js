export const routesViewTemplate = `
<section class="panel">
  <h2>冷链线路</h2>
  <p class="hint">排程视图：线路 × 批次态同源投影，批次状取自单一读取口。</p>
  <div class="form-row">
    <div><label>线路编码</label><input v-model="routeForm.route_code"/></div>
    <div><label>起点区域</label><input v-model="routeForm.origin_region"/></div>
    <div><label>终点区域</label><input v-model="routeForm.dest_region"/></div>
    <div><label>冷链时长(h)</label><input type="number" v-model.number="routeForm.cold_hours"/></div>
    <div><label>车型</label><input v-model="routeForm.vehicle_type"/></div>
  </div>
  <div class="actions"><button @click="createRoute">新建线路</button></div>
  <table class="data-table">
    <thead><tr><th>编码</th><th>起</th><th>讫</th><th>时长</th><th>车型</th><th>状态</th></tr></thead>
    <tbody>
      <tr v-for="r in routes" :key="r.id">
        <td>{{ r.route_code }}</td>
        <td>{{ r.origin_region }}</td>
        <td>{{ r.dest_region }}</td>
        <td>{{ r.cold_hours }}</td>
        <td>{{ r.vehicle_type }}</td>
        <td>{{ r.status }}</td>
      </tr>
    </tbody>
  </table>
  <h3>批次态分布(同源)</h3>
  <table class="data-table">
    <thead><tr><th>批次</th><th>同源态</th><th>封批</th><th>桩待办</th></tr></thead>
    <tbody>
      <tr v-for="s in states" :key="s.batch_id">
        <td>{{ s.batch_code }}</td>
        <td><span class="badge" :class="statusClass(s.status)">{{ s.status }}</span></td>
        <td>{{ s.sealed ? "是" : "否" }}</td>
        <td>{{ s.thaw_pending }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;
