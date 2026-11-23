export const chambersViewTemplate = `
<section class="panel">
  <h2>冷库仓间</h2>
  <p class="hint">各区域冷库仓间目标温区、在批配额与运行状态。</p>
  <div class="grid-2">
    <div>
      <motion-form class="form-block">
        <div class="form-row">
          <div><label>仓间编码</label><input v-model="chamberForm.chamber_code"/></div>
          <div><label>区域</label><input v-model="chamberForm.region"/></div>
          <div><label>名称</label><input v-model="chamberForm.name"/></div>
          <div><label>目标下限℃</label><input type="number" v-model.number="chamberForm.target_min"/></div>
          <div><label>目标上限℃</label><input type="number" v-model.number="chamberForm.target_max"/></div>
          <div><label>在批配额</label><input type="number" v-model.number="chamberForm.quota_batches"/></div>
        </div>
        <div class="actions">
          <button @click="createChamber">新建仓间</button>
          <button class="secondary" @click="refresh">刷新</button>
        </div>
      </motion-form>
    </div>
    <div class="table-wrap">
      <table class="data-table">
        <thead>
          <tr><th>编码</th><th>区域</th><th>温区</th><th>配额</th><th>状态</th><th></th></tr>
        </thead>
        <tbody>
          <tr v-for="c in chambers" :key="c.id" :class="{picked: chamberDetail && chamberDetail.chamber.id===c.id}">
            <td>{{ c.chamber_code }}</td>
            <td>{{ c.region }}</td>
            <td>{{ c.target_min }}~{{ c.target_max }}℃</td>
            <td>{{ c.quota_batches }}</td>
            <td><span class="badge" :class="statusClass(c.status)">{{ c.status }}</span></td>
            <td><button class="mini-btn" @click="loadChamberDetail(c.id)">详情</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
  <div v-if="chamberDetail" class="detail-box">
    <h3>仓间详情 · {{ chamberDetail.chamber.name }}</h3>
    <p>在批 {{ chamberDetail.active_batch_count }} · 剩余配额 {{ chamberDetail.quota_left }}</p>
    <table class="data-table compact">
      <thead><tr><th>探头</th><th>在线</th><th>校准到期</th></tr></thead>
      <tbody>
        <tr v-for="p in chamberDetail.probes" :key="p.id">
          <td>{{ p.probe_code }}</td>
          <td>{{ p.online_status }}</td>
          <td>{{ p.calibration_due }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</section>
`.replace("<motion-form class=\"form-block\">", "<div class=\"form-block\">").replace("</motion-form>", "</div>");