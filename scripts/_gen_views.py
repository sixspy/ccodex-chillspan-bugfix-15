from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "frontend/js/views"
VIEWS = [
    ("chambers", "冷库仓间", "登记仓间目标温区与在批配额。"),
    ("probes", "探头登记", "探头挂靠仓间，维护在线态与校准到期。"),
    ("batches", "温控批次", "写入温度点序列，驱动游标与封批。"),
    ("excursions", "超温游标", "对超阈批次开闭游标。"),
    ("seal", "封批升代", "生成封批快照并提升代数。"),
    ("spectrum", "温谱导出", "对已封批批次导出温谱。"),
    ("lineage", "冷链血缘", "登记批次血缘边。"),
    ("reconcile", "仓间对账", "核对配额与在批差额。"),
    ("calibration", "探头校准", "录入校准并顺延到期。"),
    ("routes", "线路计划", "维护冷链线路与时效。"),
    ("stubs", "空桩台", "承运商导入与解冻空桩。"),
]

for key, title, hint in VIEWS:
    content = f'''export const {key}ViewTemplate = `
<section class="panel">
  <h2>{title}</h2>
  <p class="hint">{hint}</p>
  <div class="grid-2">
    <div>
      <div class="form-row">
        <div>
          <label>检索</label>
          <input v-model="filter_{key}" placeholder="编码关键字"/>
        </div>
        <div>
          <label>上次操作</label>
          <input disabled :value="lastMsg_{key}"/>
        </div>
      </div>
      <div class="actions">
        <button @click="refresh">刷新</button>
      </div>
    </div>
    <div class="table-wrap">
      <table class="data-table">
        <thead><tr><th>项</th><th>值</th><th>态</th></tr></thead>
        <tbody>
          <tr v-for="(row, idx) in rows_{key}" :key="idx">
            <td>{{{{ row.k }}}}</td>
            <td>{{{{ row.v }}}}</td>
            <td><span class="badge">{{{{ row.s }}}}</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</section>
`;'''
    (ROOT / f"{key}_view.js").write_text(content, encoding="utf-8")
print("ok", len(VIEWS))