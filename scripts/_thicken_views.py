"""加厚各视图模板（业务表单与表格）。"""
from pathlib import Path

V = Path(__file__).resolve().parents[1] / "frontend/js/views"

files = {
    "probes_view.js": r'''
export const probesViewTemplate = `
<section class="panel">
  <h2>探头登记</h2>
  <p class="hint">探头须挂靠仓间；离线探头禁止新建批次。</p>
  <div class="form-row">
    <div><label>探头编码</label><input v-model="probeForm.probe_code"/></div>
    <div><label>仓间</label>
      <select v-model.number="probeForm.chamber_id">
        <option v-for="c in chambers" :key="c.id" :value="c.id">{{ c.chamber_code }} · {{ c.name }}</option>
      </select>
    </div>
    <div><label>型号</label><input v-model="probeForm.model"/></div>
    <div><label>校准到期</label><input v-model="probeForm.calibration_due" type="date"/></div>
  </div>
  <div class="actions">
    <button @click="registerProbe">登记探头</button>
    <button class="secondary" @click="refresh">刷新</button>
  </div>
  <table class="data-table">
    <thead><tr><th>编码</th><th>仓间</th><th>区域</th><th>在线</th><th>到期</th><th></th></tr></thead>
    <tbody>
      <tr v-for="p in probes" :key="p.id" @click="selectProbe(p)">
        <td>{{ p.probe_code }}</td>
        <td>{{ p.chamber_code }}</td>
        <td>{{ p.region }}</td>
        <td><span class="badge" :class="p.online_status==='在线'?'pass':'fail'">{{ p.online_status }}</span></td>
        <td>{{ p.calibration_due }}</td>
        <td><button class="mini-btn" @click.stop="loadProbeDetail(p.id)">校准史</button></td>
      </tr>
    </tbody>
  </table>
  <div v-if="probeDetail" class="detail-box">
    <h3>探头 {{ probeDetail.probe.probe_code }}</h3>
    <p>目标温区 {{ probeDetail.probe.target_min }}~{{ probeDetail.probe.target_max }}℃</p>
    <ul><li v-for="c in probeDetail.calibrations" :key="c.id">{{ c.calibrated_at }} 偏移 {{ c.offset_c }}℃ 至 {{ c.valid_until }}</li></ul>
  </div>
</section>
`;''',
    "batches_view.js": r'''
export const batchesViewTemplate = `
<section class="panel">
  <h2>温控批次入库</h2>
  <p class="hint">写入温度点 JSON 数组；入库后可开超温游标与封批。</p>
  <div class="form-row">
    <div><label>仓间</label>
      <select v-model.number="batchForm.chamber_id"><option v-for="c in chambers" :key="c.id" :value="c.id">{{ c.chamber_code }}</option></select>
    </div>
    <div><label>探头</label>
      <select v-model.number="batchForm.probe_id"><option v-for="p in batchProbes" :key="p.id" :value="p.id">{{ p.probe_code }}</option></select>
    </div>
    <div><label>货载编号</label><input v-model="batchForm.cargo_ref"/></div>
    <div><label>批次编码(可空)</label><input v-model="batchForm.batch_code"/></div>
  </div>
  <label>温度点 JSON</label>
  <textarea v-model="batchForm.points_json" rows="4" placeholder='[{"t":"08:00","c":-19}]'></textarea>
  <div class="actions">
    <button @click="createBatch">新建批次</button>
    <button class="secondary" @click="refresh">刷新</button>
  </div>
  <table class="data-table">
    <thead><tr><th>批次</th><th>仓间</th><th>探头</th><th>状态</th><th>代</th><th>极值</th><th></th></tr></thead>
    <tbody>
      <tr v-for="b in batches" :key="b.id" @click="selectBatch(b)">
        <td>{{ b.batch_code }}</td>
        <td>{{ b.chamber_code }}</td>
        <td>{{ b.probe_code }}</td>
        <td><span class="badge" :class="statusClass(b.status)">{{ b.status }}</span></td>
        <td>{{ b.generation }}</td>
        <td>{{ fmtTemp(b.min_observed) }} / {{ fmtTemp(b.max_observed) }}</td>
        <td><button class="mini-btn" @click.stop="loadBatchDetail(b.id)">详情</button></td>
      </tr>
    </tbody>
  </table>
  <div v-if="batchDetail" class="detail-box">
    <h3>{{ batchDetail.batch.batch_code }} · {{ batchDetail.batch.cargo_ref }}</h3>
    <p>点数 {{ batchDetail.batch.temp_points.length }} · 游标 {{ batchDetail.excursions.length }} 条</p>
  </div>
</section>
`;''',
    "excursions_view.js": r'''
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
        <td><span class="badge" :class="e.status==='开放'?'fail':'pass'">{{ e.status }}</span></td>
        <td>{{ e.opened_at }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;''',
    "seal_view.js": r'''
export const sealViewTemplate = `
<section class="panel">
  <h2>封批升代</h2>
  <p class="hint">校准有效且无开放游标时方可封批。</p>
  <div class="form-row">
    <div><label>批次</label>
      <select v-model.number="sealForm.batch_id"><option v-for="b in sealableBatches" :key="b.id" :value="b.id">{{ b.batch_code }}</option></select>
    </div>
    <div><label>快照附言</label><input v-model="sealForm.manifest"/></div>
  </div>
  <div class="actions"><button @click="doSeal">执行封批</button></div>
  <table class="data-table">
    <thead><tr><th>批次</th><th>代</th><th>封批时间</th><th>附言摘要</th></tr></thead>
    <tbody>
      <tr v-for="s in seals" :key="s.id">
        <td>{{ s.batch_code }}</td>
        <td>{{ s.batch_generation }}</td>
        <td>{{ s.sealed_at }}</td>
        <td>{{ shortText(s.manifest) }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;''',
    "spectrum_view.js": r'''
export const spectrumViewTemplate = `
<section class="panel">
  <h2>温谱导出</h2>
  <p class="hint">仅已封批批次可导出；同代重复导出将被拒绝。</p>
  <div class="form-row">
    <div><label>已封批批次</label>
      <select v-model.number="spectrumForm.batch_id"><option v-for="b in sealedBatches" :key="b.id" :value="b.id">{{ b.batch_code }} G{{ b.generation }}</option></select>
    </div>
  </div>
  <div class="actions"><button @click="doSpectrum">导出温谱</button></div>
  <table class="data-table">
    <thead><tr><th>导出号</th><th>批次</th><th>点数</th><th>校验</th><th>状态</th></tr></thead>
    <tbody>
      <tr v-for="x in spectrumExports" :key="x.id">
        <td>{{ x.export_ref }}</td>
        <td>{{ x.batch_code }}</td>
        <td>{{ x.point_count }}</td>
        <td class="mono">{{ x.checksum }}</td>
        <td>{{ x.status }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;''',
    "lineage_view.js": r'''
export const lineageViewTemplate = `
<section class="panel">
  <h2>冷链血缘</h2>
  <div class="form-row">
    <div><label>来源批次ID</label><input type="number" v-model.number="lineageForm.from_batch_id"/></div>
    <div><label>目标批次ID</label><input type="number" v-model.number="lineageForm.to_batch_id"/></div>
    <div><label>类型</label><input v-model="lineageForm.edge_type"/></div>
    <div><label>说明</label><input v-model="lineageForm.detail"/></div>
  </div>
  <div class="actions"><button @click="addLineage">登记血缘边</button></div>
  <table class="data-table">
    <thead><tr><th>自</th><th>至</th><th>类型</th><th>说明</th><th>时间</th></tr></thead>
    <tbody>
      <tr v-for="e in lineageEdges" :key="e.id">
        <td>{{ e.from_code }}</td>
        <td>{{ e.to_code || '—' }}</td>
        <td>{{ e.edge_type }}</td>
        <td>{{ e.detail }}</td>
        <td>{{ e.created_at }}</td>
      </tr>
    </tbody>
  </table>
</section>
`;''',
    "reconcile_view.js": r'''
export const reconcileViewTemplate = `
<section class="panel">
  <h2>仓间对账互证</h2>
  <div class="form-row">
    <div><label>仓间编码</label><input v-model="reconCode"/></div>
    <div><label>批次互证编码</label><input v-model="proofCode"/></div>
  </div>
  <div class="actions">
    <button @click="loadRecon">对账单仓</button>
    <button class="secondary" @click="loadProof">批次互证</button>
    <button class="secondary" @click="loadReconAll">全仓对账</button>
  </div>
  <div v-if="reconOne" class="detail-box">
    <p>配额 {{ reconOne.quota_batches }} · 在批 {{ reconOne.active_batches }} · <span :class="reconOne.balanced?'ok':'bad'">{{ reconOne.balanced?'平衡':'失衡' }}</span></p>
  </div>
  <motion-proof v-if="proofOne" class="detail-box">
    <p>状态 {{ proofOne.status }} · 开放游标 {{ proofOne.open_excursions }} · 温谱 {{ proofOne.spectrum_exports }}</p>
  </motion-proof>
  <table class="data-table">
    <thead><tr><th>仓间</th><th>区域</th><th>在批</th><th>余配额</th><th>平衡</th></tr></thead>
    <tbody>
      <tr v-for="r in reconAll.items || []" :key="r.chamber_code">
        <td>{{ r.chamber_code }}</td>
        <td>{{ r.region }}</td>
        <td>{{ r.active_batches }}</td>
        <td>{{ r.quota_left }}</td>
        <td>{{ r.balanced ? '是' : '否' }}</td>
      </tr>
    </tbody>
  </table>
</section>
`.replace("<motion-proof", "<div").replace("</motion-proof>", "</div>"),
    "calibration_view.js": r'''
export const calibrationViewTemplate = `
<section class="panel">
  <h2>探头校准</h2>
  <div class="form-row">
    <div><label>探头</label>
      <select v-model.number="calForm.probe_id"><option v-for="p in probes" :key="p.id" :value="p.id">{{ p.probe_code }}</option></select>
    </div>
    <div><label>偏移℃</label><input type="number" step="0.1" v-model.number="calForm.offset_c"/></div>
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
`;''',
    "routes_view.js": r'''
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
`;''',
    "stubs_view.js": r'''
export const stubsViewTemplate = `
<section class="panel">
  <h2>空桩台</h2>
  <p class="hint">承运商导入与解冻事件仅登记任务表，不改批次主表。</p>
  <div class="grid-2">
    <div>
      <h3>承运商导入空桩</h3>
      <motion-f class="form-row">
        <motion-i><label>承运商</label><input v-model="carrierForm.carrier_name"/></motion-i>
        <div><label>行数</label><input type="number" v-model.number="carrierForm.row_count"/></div>
      </motion-f>
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
`.replace("<motion-f", "<div").replace("</motion-f>", "</div>").replace("<motion-i>", "<div>").replace("</motion-i>", "</div>"),
}

for name, body in files.items():
    (V / name).write_text(body.strip() + "\n", encoding="utf-8")
print("thickened", len(files))