import { createApi } from "./api.js";
import { chambersViewTemplate } from "./views/chambers_view.js";
import { probesViewTemplate } from "./views/probes_view.js";
import { batchesViewTemplate } from "./views/batches_view.js";
import { excursionsViewTemplate } from "./views/excursions_view.js";
import { sealViewTemplate } from "./views/seal_view.js";
import { spectrumViewTemplate } from "./views/spectrum_view.js";
import { lineageViewTemplate } from "./views/lineage_view.js";
import { reconcileViewTemplate } from "./views/reconcile_view.js";
import { calibrationViewTemplate } from "./views/calibration_view.js";
import { routesViewTemplate } from "./views/routes_view.js";
import { stubsViewTemplate } from "./views/stubs_view.js";

const { createApp, ref, computed, watch, onMounted } = Vue;

createApp({
  setup() {
    const token = ref(localStorage.getItem("chillspan_token") || "");
    const user = ref(localStorage.getItem("chillspan_user") || "");
    const username = ref("admin");
    const password = ref("123456");
    const err = ref("");
    const actionErr = ref("");
    const actionOk = ref("");
    const tab = ref(0);
    const nav = [
      "仓间",
      "探头",
      "批次",
      "超温游标",
      "封批",
      "温谱",
      "血缘",
      "对账",
      "校准",
      "线路",
      "空桩",
    ];

    const chambers = ref([]);
    const probes = ref([]);
    const batches = ref([]);
    const excursions = ref([]);
    const seals = ref([]);
    const spectrumExports = ref([]);
    const lineageEdges = ref([]);
    const calibrations = ref([]);
    const routes = ref([]);
    const carrierJobs = ref([]);
    const thawJobs = ref([]);
    const states = ref([]);
    const stateSummary = ref({});
    const dash = ref({});

    const chamberDetail = ref(null);
    const probeDetail = ref(null);
    const batchDetail = ref(null);
    const selectedExcursion = ref(null);
    const reconOne = ref(null);
    const proofOne = ref(null);
    const reconAllItems = ref([]);
    const reconCode = ref("CK-HD-01");
    const proofCode = ref("TB-CK-HD-01-002");

    const chamberForm = ref({
      chamber_code: "CK-NEW-01",
      region: "华东",
      name: "新建冷库",
      target_min: -20,
      target_max: -16,
      quota_batches: 12,
    });
    const probeForm = ref({
      probe_code: "PR-NEW-01",
      chamber_id: 1,
      model: "T-200",
      calibration_due: "2027-06-01",
    });
    const batchForm = ref({
      chamber_id: 1,
      probe_id: 1,
      cargo_ref: "试运行货载",
      batch_code: "",
      points_json: '[{"t":"08:00","c":-19.1},{"t":"09:00","c":-18.9}]',
    });
    const excOpenForm = ref({ batch_id: 0, threshold: null, note: "" });
    const sealForm = ref({ batch_id: 0, manifest: "" });
    const spectrumForm = ref({ batch_id: 0 });
    const lineageForm = ref({
      from_batch_id: 1,
      to_batch_id: 2,
      edge_type: "分装衍生",
      detail: "冷库内分装",
    });
    const calForm = ref({
      probe_id: 1,
      offset_c: 0.1,
      valid_until: "2027-12-01",
      officer: "值班员",
    });
    const routeForm = ref({
      route_code: "RT-NEW-01",
      origin_region: "华东",
      dest_region: "西南",
      cold_hours: 28,
      vehicle_type: "冷藏车",
    });
    const carrierForm = ref({ carrier_name: "顺冷物流", row_count: 80 });
    const thawForm = ref({ batch_id: null, thaw_minutes: 15 });

    function logout() {
      token.value = "";
      user.value = "";
      localStorage.removeItem("chillspan_token");
      localStorage.removeItem("chillspan_user");
    }

    const api = createApi(
      () => token.value,
      () => logout()
    );

    const batchProbes = computed(() =>
      probes.value.filter((p) => p.chamber_id === batchForm.value.chamber_id)
    );
    const openableBatches = computed(() =>
      batches.value.filter((b) => b.status !== "已封批" && b.status !== "草稿")
    );
    const sealableBatches = computed(() =>
      batches.value.filter((b) => b.status === "已入库" || b.status === "超温处理中")
    );
    const sealedBatches = computed(() =>
      batches.value.filter((b) => b.status === "已封批")
    );
    // 五面同源：按批次 id 索引单一态投影，供批次/封存/曲线/排程/任务五视图共用。
    const stateByBatch = computed(() => {
      const m = {};
      for (const s of states.value) m[s.batch_id] = s;
      return m;
    });
    function faceOf(batchId) {
      return stateByBatch.value[batchId] || null;
    }
    function faceStatus(batchId) {
      const f = faceOf(batchId);
      return f ? f.status : "—";
    }

    function fmtTemp(n) {
      if (n === null || n === undefined || n === "") return "—";
      return Number(n).toFixed(1) + "℃";
    }
    function statusClass(s) {
      if (!s) return "frozen";
      if (s.includes("封批")) return "pass";
      if (s.includes("超温")) return "fail";
      if (s.includes("草稿")) return "frozen";
      return "done";
    }
    function probeOnlineClass(s) {
      return s === "在线" ? "pass" : "fail";
    }
    function excursionClass(s) {
      return s === "开放" ? "fail" : "pass";
    }
    function shortText(t) {
      if (!t) return "";
      return String(t).slice(0, 48) + (String(t).length > 48 ? "…" : "");
    }

    async function login() {
      err.value = "";
      const r = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.value,
          password: password.value,
        }),
      });
      const j = await r.json();
      if (!r.ok) {
        err.value = j.detail || "登录失败";
        return;
      }
      token.value = j.token;
      user.value = j.username;
      localStorage.setItem("chillspan_token", j.token);
      localStorage.setItem("chillspan_user", j.username);
      await refresh();
    }

    function clearFlash() {
      actionErr.value = "";
      actionOk.value = "";
    }
    function flashOk(msg) {
      actionOk.value = msg;
      actionErr.value = "";
    }
    function flashErr(e) {
      actionErr.value = e.message || String(e);
      actionOk.value = "";
    }

    async function refresh() {
      if (!token.value) return;
      clearFlash();
      try {
        const [ch, pr, bt, ex, sl, sp, lg, cal, rt, d, cj, tj, st] = await Promise.all([
          api.chambers(),
          api.probes(),
          api.batches(),
          api.excursions(),
          api.seals(),
          api.spectrumList(),
          api.lineage(),
          api.calibrations(),
          api.routes(),
          api.dashboard(),
          api.carrierJobs(),
          api.thawJobs(),
          api.state(),
        ]);
        chambers.value = ch.items || [];
        probes.value = pr.items || [];
        batches.value = bt.items || [];
        excursions.value = ex.items || [];
        seals.value = sl.items || [];
        spectrumExports.value = sp.items || [];
        lineageEdges.value = lg.items || [];
        calibrations.value = cal.items || [];
        routes.value = rt.items || [];
        dash.value = d || {};
        carrierJobs.value = cj.items || [];
        thawJobs.value = tj.items || [];
        states.value = st.items || [];
        stateSummary.value = st.summary || {};

        if (chambers.value.length && !probeForm.value.chamber_id) {
          probeForm.value.chamber_id = chambers.value[0].id;
        }
        if (chambers.value.length) {
          batchForm.value.chamber_id = batchForm.value.chamber_id || chambers.value[0].id;
        }
        if (batchProbes.value.length) {
          batchForm.value.probe_id = batchProbes.value[0].id;
        }
        if (openableBatches.value.length) {
          excOpenForm.value.batch_id = openableBatches.value[0].id;
        }
        if (sealableBatches.value.length) {
          sealForm.value.batch_id = sealableBatches.value[0].id;
        }
        if (sealedBatches.value.length) {
          spectrumForm.value.batch_id = sealedBatches.value[0].id;
        }
        if (probes.value.length) {
          calForm.value.probe_id = probes.value[0].id;
        }
      } catch (e) {
        flashErr(e);
      }
    }

    watch(
      () => batchForm.value.chamber_id,
      () => {
        if (batchProbes.value.length) {
          batchForm.value.probe_id = batchProbes.value[0].id;
        }
      }
    );

    async function createChamber() {
      clearFlash();
      try {
        await api.createChamber(chamberForm.value);
        flashOk("仓间已登记");
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }
    async function loadChamberDetail(id) {
      chamberDetail.value = await api.chamber(id);
    }

    async function registerProbe() {
      clearFlash();
      try {
        await api.registerProbe(probeForm.value);
        flashOk("探头已登记");
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }
    async function loadProbeDetail(id) {
      probeDetail.value = await api.probe(id);
    }
    function selectProbe() {}

    async function createBatch() {
      clearFlash();
      try {
        let points = [];
        if (batchForm.value.points_json.trim()) {
          points = JSON.parse(batchForm.value.points_json);
        }
        const payload = {
          chamber_id: batchForm.value.chamber_id,
          probe_id: batchForm.value.probe_id,
          cargo_ref: batchForm.value.cargo_ref,
          temp_points: points,
        };
        if (batchForm.value.batch_code) payload.batch_code = batchForm.value.batch_code;
        const row = await api.createBatch(payload);
        flashOk(`批次 ${row.batch_code} 已写入`);
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }
    async function loadBatchDetail(id) {
      batchDetail.value = await api.batch(id);
    }
    function selectBatch() {}

    async function openExcursion() {
      clearFlash();
      try {
        const payload = {
          batch_id: excOpenForm.value.batch_id,
          note: excOpenForm.value.note,
        };
        if (excOpenForm.value.threshold != null) payload.threshold = excOpenForm.value.threshold;
        const row = await api.openExcursion(payload);
        flashOk(`游标 ${row.cursor_key} 已开放`);
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }
    async function closeSelectedExcursion() {
      clearFlash();
      try {
        if (!selectedExcursion.value) throw new Error("请点选游标行");
        await api.closeExcursion({
          cursor_id: selectedExcursion.value.id,
          note: "前端闭环",
        });
        flashOk("游标已闭");
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    async function doSeal() {
      clearFlash();
      try {
        const row = await api.seal(sealForm.value);
        flashOk(`封批完成 代${row.generation}`);
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    async function doSpectrum() {
      clearFlash();
      try {
        const row = await api.spectrumExport({ batch_id: spectrumForm.value.batch_id });
        flashOk(`温谱 ${row.export_ref}`);
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    async function addLineageEdge() {
      clearFlash();
      try {
        await api.addLineage(lineageForm.value);
        flashOk("血缘边已登记");
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    async function loadRecon() {
      clearFlash();
      try {
        reconOne.value = await api.reconcileOne(reconCode.value);
        flashOk("单仓对账已加载");
      } catch (e) {
        flashErr(e);
      }
    }
    async function loadProof() {
      clearFlash();
      try {
        proofOne.value = await api.proofBatch(proofCode.value);
        flashOk("批次互证已加载");
      } catch (e) {
        flashErr(e);
      }
    }
    async function loadReconAll() {
      clearFlash();
      try {
        const r = await api.reconcile();
        reconAllItems.value = r.items || [];
        flashOk("全仓对账已刷新");
      } catch (e) {
        flashErr(e);
      }
    }

    async function addCalibration() {
      clearFlash();
      try {
        await api.addCalibration(calForm.value);
        flashOk("校准记录已写入");
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    async function createRoute() {
      clearFlash();
      try {
        await api.createRoute(routeForm.value);
        flashOk("线路已创建");
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    async function doCarrierStub() {
      clearFlash();
      try {
        const row = await api.carrierStub(carrierForm.value);
        flashOk(`承运商空桩 #${row.job_id}`);
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }
    async function doThawStub() {
      clearFlash();
      try {
        const row = await api.thawStub(thawForm.value);
        flashOk(`解冻空桩 #${row.job_id} · ${row.track || "甲"}轨`);
        await refresh();
      } catch (e) {
        flashErr(e);
      }
    }

    onMounted(async () => {
      if (token.value) await refresh();
    });

    return {
      token,
      user,
      username,
      password,
      err,
      actionErr,
      actionOk,
      tab,
      nav,
      chambers,
      probes,
      batches,
      excursions,
      seals,
      spectrumExports,
      lineageEdges,
      calibrations,
      routes,
      carrierJobs,
      thawJobs,
      states,
      stateSummary,
      dash,
      chamberDetail,
      probeDetail,
      batchDetail,
      selectedExcursion,
      reconOne,
      proofOne,
      reconAllItems,
      reconCode,
      proofCode,
      chamberForm,
      probeForm,
      batchForm,
      excOpenForm,
      sealForm,
      spectrumForm,
      lineageForm,
      calForm,
      routeForm,
      carrierForm,
      thawForm,
      batchProbes,
      openableBatches,
      sealableBatches,
      sealedBatches,
      stateByBatch,
      faceOf,
      faceStatus,
      login,
      logout,
      refresh,
      clearFlash,
      fmtTemp,
      statusClass,
      probeOnlineClass,
      excursionClass,
      shortText,
      createChamber,
      loadChamberDetail,
      registerProbe,
      loadProbeDetail,
      selectProbe,
      createBatch,
      loadBatchDetail,
      selectBatch,
      openExcursion,
      closeSelectedExcursion,
      doSeal,
      doSpectrum,
      addLineageEdge,
      loadRecon,
      loadProof,
      loadReconAll,
      addCalibration,
      createRoute,
      doCarrierStub,
      doThawStub,
    };
  },
  template: `
  <div v-if="!token" class="login-shell">
    <div class="login-card">
      <h1>冷链温谱管道</h1>
      <p class="sub">探头批次入库、超温游标闭环、封批升代、温谱导出与血缘对账。</p>
      <label>账号</label>
      <input v-model="username"/>
      <label>密码</label>
      <input type="password" v-model="password" @keyup.enter="login"/>
      <button @click="login">进入监控台</button>
      <div class="err" v-if="err">{{ err }}</div>
    </div>
  </div>
  <div v-else class="console">
    <header class="topbar">
      <div class="brand">
        冷链温谱管道
        <small>深青监控台 · 仓储温控数据工程</small>
      </div>
      <div class="gauges">
        <div class="gauge"><span class="k">仓间</span><span class="v">{{ dash.chambers || 0 }}</span></div>
        <div class="gauge"><span class="k">探头</span><span class="v">{{ dash.probes || 0 }}</span></div>
        <div class="gauge"><span class="k">在批</span><span class="v">{{ dash.batches || 0 }}</span></div>
        <div class="gauge warn"><span class="k">开放游标</span><span class="v">{{ dash.open_excursions || 0 }}</span></div>
        <div class="gauge"><span class="k">已封批</span><span class="v">{{ dash.sealed_batches || 0 }}</span></div>
      </div>
      <div class="top-meta">
        <span>{{ user }}</span>
        <button @click="refresh">刷新</button>
        <button @click="logout">退出</button>
      </div>
    </header>
    <div class="body">
      <aside class="rail">
        <button v-for="(n,i) in nav" :key="n" :class="{active: tab===i}" @click="tab=i">{{ n }}</button>
      </aside>
      <main class="main">
        <div class="action-err" v-if="actionErr">{{ actionErr }}</div>
        <div class="ok-msg" v-if="actionOk">{{ actionOk }}</div>
        <div v-show="tab===0">${chambersViewTemplate}</div>
        <div v-show="tab===1">${probesViewTemplate}</div>
        <div v-show="tab===2">${batchesViewTemplate}</div>
        <div v-show="tab===3">${excursionsViewTemplate}</div>
        <div v-show="tab===4">${sealViewTemplate}</div>
        <div v-show="tab===5">${spectrumViewTemplate}</div>
        <div v-show="tab===6">${lineageViewTemplate}</div>
        <div v-show="tab===7">${reconcileViewTemplate}</div>
        <div v-show="tab===8">${calibrationViewTemplate}</div>
        <div v-show="tab===9">${routesViewTemplate}</div>
        <div v-show="tab===10">${stubsViewTemplate}</div>
      </main>
    </div>
  </div>
  `,
}).mount("#app");