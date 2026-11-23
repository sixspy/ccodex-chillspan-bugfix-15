export const routesViewTemplate = `
<section class="panel">
  <h2>冷链线路</h2>
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
</section>
`;