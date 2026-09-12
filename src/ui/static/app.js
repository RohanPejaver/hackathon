/* Station display + inspector renderer. One snapshot in, DOM out. No library, no build step.
   Wire: {state_summary, interventions} is the core's DisplayPayload verbatim; `runtime` is the
   composition root's block (clock, health, log tail, zones, menu). The worker never mutates
   state: every tap is POST /action, which becomes an event (22). */
(() => {
  const page = document.body.dataset.page;
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const icon = (n) => `<svg class="ph"><use href="/static/vendor/icons/phosphor-sprite.svg#ph-${n}"/></svg>`;
  const KIND_ICON = { GLOVES: 'hand', TOOL: 'knife', SURFACE: 'square', CONTAINER: 'jar', FOOD: 'bread' };
  const ACTION_ICON = { NEW_GLOVES: 'hand', SWAP_TOOL: 'arrows-clockwise', SWAP_SURFACE: 'square', USE_SEALED_BACKUP: 'warning', SEQUENCE_TICKETS: 'list-checks', VERIFY: 'check-square', HOLD: 'pause', REMAKE: 'arrow-counter-clockwise' };
  const ASSERT_LABEL = { NEW_GLOVES: 'Already changed', SWAP_TOOL: 'Already swapped', SWAP_SURFACE: 'Already swapped', USE_SEALED_BACKUP: 'Using sealed backup', VERIFY: 'Already done' };
  const GRADE_ABBR = { OBSERVED: 'obs', INFERRED: 'inf', ASSERTED: 'asr', PESSIMISTIC: 'pes' };
  const MODE_TEXT = { FULL: 'FULL', PROTOCOL_ONLY: 'PROTOCOL ONLY — VISION UNAVAILABLE', REPLAY: 'REPLAY', CALIBRATION: 'CALIBRATION' };
  const KIND_ORDER = { GLOVES: 0, TOOL: 1, SURFACE: 2, CONTAINER: 3, FOOD: 4 };
  const OPEN = new Set(['RAISED', 'ACKNOWLEDGED', 'ESCALATED']);
  const LIVE_TICKET = new Set(['RECEIVED', 'BLOCKED', 'BOUND', 'IN_PREP', 'COMPLETE', 'HELD']);

  let snap = null;
  const now = () => snap.runtime.time.t;
  const zoneOf = (id) => snap.runtime.zones.find((z) => z.zone_id === id);
  const menuName = (id) => (snap.runtime.menu.find((m) => m.item_id === id) || { display_name: id }).display_name;

  const fmtT = (t) => {
    if (t == null) return '—';
    if (snap && snap.runtime.time.kind === 'WALL') return new Date(t).toTimeString().slice(0, 8);
    const s = Math.floor(t / 1000);
    return `+${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}.${Math.floor((t % 1000) / 100)}`;
  };
  const ago = (t) => {
    if (t == null) return 'never';
    const d = Math.max(0, now() - t);
    return d < 1000 ? 'now' : d < 60000 ? `${Math.floor(d / 1000)}s` : `${Math.floor(d / 60000)}m`;
  };

  async function act(body) {
    const r = await fetch('/action', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ worker_slot: 0, ...body }) });
    if (!r.ok) console.warn('action refused', await r.text());
  }
  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (b) act(JSON.parse(b.dataset.act));
  });

  function renderTop(s) {
    const h = s.runtime.health;
    $('station').textContent = s.state_summary.station_id;
    const down = h.reasoning === 'DOWN';
    $('banner').dataset.mode = down ? 'DOWN' : s.state_summary.mode;
    $('banner-text').textContent = down ? 'REASONING DOWN — PROTOCOL ONLY' : MODE_TEXT[s.state_summary.mode];
    $('banner-why').textContent = h.message || '';
    $('h-vision').textContent = h.vision;
    $('h-reasoning').textContent = h.reasoning;
    $('h-late').textContent = `${Math.round(h.late_rate * 100)}%`;
    $('h-rejected').textContent = h.rejected_events;
    $('clock').textContent = fmtT(now());
    if ($('h-cfg')) { $('h-cfg').textContent = `v${s.state_summary.config_version}`; $('h-kv').textContent = `v${s.state_summary.knowledge_version}`; }
  }

  function restrLine(r) {
    const txt = r.resolution === 'RESOLVED' ? (r.allergen_ids.length ? r.allergen_ids.join(', ') : r.kind) : r.resolution;
    return `<div class="restr" data-resolution="${r.resolution}">${esc(txt)} <span class="raw">“${esc(r.raw_text)}”</span></div>`;
  }
  function ticketButtons(t) {
    if (page !== 'worker') return '';
    const b = (label, act, kind = 'quiet') => `<button class="btn small" data-kind="${kind}" data-act='${esc(JSON.stringify({ ...act, ticket_id: t.ticket_id }))}'>${label}</button>`;
    const bindable = t.lifecycle === 'RECEIVED' && t.restrictions.every((r) => r.resolution === 'RESOLVED');
    if (t.lifecycle === 'RECEIVED') return bindable ? b('Bind', { kind: 'BIND_TICKET' }, 'primary') : '<span class="micro">normalizing…</span>';
    if (t.lifecycle === 'BOUND') return b('Start prep', { kind: 'PREP_STARTED' });
    if (t.lifecycle === 'IN_PREP') return b('Item complete', { kind: 'ITEM_COMPLETE' });
    if (t.lifecycle === 'COMPLETE') return b('Send', { kind: 'RESOLVE_HOLD' }, 'primary');
    if (t.lifecycle === 'BLOCKED') return '<span class="micro">restriction unresolved — ask front of house</span>';
    return '';
  }
  function renderTickets(s) {
    const live = s.state_summary.tickets.filter((t) => LIVE_TICKET.has(t.lifecycle));
    $('tickets-count').textContent = live.length;
    const cards = live.map((t) => `
      <div class="ticket" data-lifecycle="${t.lifecycle}" data-restricted="${t.restrictions.some((r) => r.allergen_ids.length || r.resolution !== 'RESOLVED') ? 1 : 0}">
        <div class="row"><span class="id">#${esc(t.ticket_id)}</span><span class="life micro">${t.lifecycle.replace('_', ' ')}</span></div>
        <div class="items">${t.items.map((i) => esc(menuName(i))).join(' · ')}</div>
        ${t.restrictions.map(restrLine).join('')}
        <div class="row" style="margin-top:6px">${ticketButtons(t)}</div>
      </div>`);
    const form = page === 'worker' ? `
      <div class="ticket" data-lifecycle="RECEIVED">
        <div class="micro" style="margin-bottom:6px">New ticket</div>
        <div class="row"><input id="nt-id" class="mono" placeholder="id" size="5"> <select id="nt-item">${s.runtime.menu.map((m) => `<option value="${esc(m.item_id)}">${esc(m.display_name)}</option>`).join('')}</select></div>
        <div class="row" style="margin-top:6px"><input id="nt-restr" placeholder="restriction note (optional)" style="flex:1"> <button class="btn small" id="nt-go">Enter</button></div>
      </div>` : '';
    const keep = { id: $('nt-id') && $('nt-id').value, restr: $('nt-restr') && $('nt-restr').value, item: $('nt-item') && $('nt-item').value, focus: document.activeElement && document.activeElement.id };
    $('tickets').innerHTML = (cards.join('') || '<div class="empty">No tickets</div>') + form;
    const go = $('nt-go');
    if (go) {
      if (keep.id) $('nt-id').value = keep.id;
      if (keep.restr) $('nt-restr').value = keep.restr;
      if (keep.item) $('nt-item').value = keep.item;
      if (keep.focus && $(keep.focus)) $(keep.focus).focus();
      go.onclick = () => {
        const id = $('nt-id').value.trim(); if (!id) return;
        const raw = $('nt-restr').value.trim();
        act({ kind: 'NEW_TICKET', ticket_id: id, items: [$('nt-item').value], restrictions: raw ? [{ raw_text: raw }] : [] });
        $('nt-id').value = ''; $('nt-restr').value = '';
      };
    }
  }

  function eventLine(e) {
    return `<div class="log-line" data-mutates="${e.mutates_state ? 1 : 0}" data-source="${e.source}" data-late="${e.late ? 1 : 0}">
      <span class="t">${fmtT(e.t_occurred)}</span><span class="type">${esc(e.type)}</span><span class="parts">${esc(e.summary)}</span><span class="grade">${esc(e.grade || '')}</span></div>`;
  }
  function renderLog(s, upto) {
    const evs = upto == null ? s.runtime.recent_events : s.runtime.recent_events.filter((e) => e.seq <= upto);
    $('log-count').textContent = `seq ${s.runtime.seq}`;
    const el = $('log');
    el.innerHTML = evs.map(eventLine).join('') || '<div class="empty">No observations yet</div>';
    el.scrollTop = el.scrollHeight;
  }

  function tile(c) {
    const taints = Object.values(c.taints);
    const tainted = taints.length > 0;
    const zone = c.home_zone ? zoneOf(c.home_zone) : null;
    const shared = c.kind === 'CONTAINER' && zone && zone.kind === 'INGREDIENT';
    const chips = taints.map((t) => `<span class="taint" data-grade="${t.grade}" data-strength="${t.strength}">${esc(t.allergen_id)}<span class="g">${GRADE_ABBR[t.grade]}${t.hops ? ` h${t.hops}` : ''}${t.strength === 'POSSIBLE' ? ' ?' : ''}</span></span>`).join('');
    const holds = shared && zone.allergens.length ? `<span class="micro">holds ${esc(zone.allergens.join(', '))}</span>` : '';
    const sharedLine = tainted && shared ? `<div class="shared">${icon('warning')} Shared container — ${esc([...new Set(taints.map((t) => t.allergen_id))].join(', '))} — affects all future tickets</div>` : '';
    const asserted = c.asserted_at != null && !tainted ? `<span class="micro">asserted ${ago(c.asserted_at)}</span>` : '';
    return `<div class="tile" data-epi="${c.epistemic}" data-tainted="${tainted ? 1 : 0}" data-kind="${c.kind}">
      <div class="tile-head">${icon(KIND_ICON[c.kind])}<span class="id">${esc(c.carrier_id)}</span><span class="kind micro">${c.kind}</span></div>
      <div class="tile-taints">${chips || holds}</div>${sharedLine}
      <div class="tile-foot"><span class="epi">${c.epistemic}</span>${asserted}<span class="ago">${c.epistemic === 'UNKNOWN' ? 'not observed' : `seen ${ago(c.last_observed_at)}`}</span></div>
    </div>`;
  }
  function renderGrid(s) {
    const cs = [...s.state_summary.carriers].sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind] || a.carrier_id.localeCompare(b.carrier_id));
    $('carriers-count').textContent = cs.length;
    $('grid').innerHTML = cs.map(tile).join('');
  }

  function traceLines(d) {
    return d.map((st) => st.rule_id === 'absence'
      ? `<div class="trace-line absent"><span class="t">—</span><span>-- ${esc(st.narrative)} --</span></div>`
      : `<div class="trace-line ${st.rule_id === 'alert' || st.rule_id.startsWith('pathway') || st.rule_id.startsWith('precondition') ? 'rule' : 'event'}"><span class="t">${fmtT(st.t_occurred)}</span><span class="type">${esc(st.rule_id)}</span><span class="delta">${esc(st.narrative)}</span><span class="grade">${esc(st.grade || '')}</span></div>`).join('');
  }
  function renderRisk(s) {
    const open = s.interventions.filter((a) => OPEN.has(a.state)).sort((a, b) => b.tier - a.tier || a.raised_at - b.raised_at);
    $('alerts-count').textContent = open.length;
    const all = page === 'inspector' ? [...s.interventions].sort((a, b) => b.updated_at - a.updated_at) : open;
    $('risk').innerHTML = all.map((a) => `
      <div class="alert" data-tier="${a.tier}">
        <div class="row"><span class="micro">Tier ${a.tier} · #${esc(a.ticket_id)} · ${esc(a.allergen_id)}</span><span class="state micro">${esc(a.state)}</span></div>
        <div class="head">${esc(a.headline)}</div>
        <div class="trace">${traceLines(a.derivation)}</div>
      </div>`).join('') || '<div class="empty">Quiet</div>';
  }

  function surfaceFor(s) {
    const open = s.interventions.filter((a) => OPEN.has(a.state) && !(a.dismissed_until != null && a.dismissed_until > now()));
    open.sort((a, b) => b.tier - a.tier || a.raised_at - b.raised_at);
    if (open.length) return { alert: open[0] };
    const held = s.state_summary.tickets.find((t) => t.lifecycle === 'HELD');
    return held ? { held } : {};
  }
  function renderSurface(s) {
    const el = $('surface');
    const { alert: a, held } = surfaceFor(s);
    if (!a && !held) {
      el.dataset.tier = 'none';
      const multi = s.state_summary.conditions.includes('MULTI_RESTRICTION');
      el.innerHTML = `<div class="label micro">${multi ? 'Two active restrictions — sequence them' : 'Station quiet'}</div><h1 class="headline">Nothing to do</h1>`;
      return;
    }
    if (held) {
      el.dataset.tier = '2';
      el.innerHTML = `<div class="label micro">Tier 2 · Hold · Ticket ${esc(held.ticket_id)} · awaiting release</div>
        <h1 class="headline">HELD — TICKET ${esc(held.ticket_id)}</h1>
        <div class="actions"><button class="btn" data-kind="primary" data-act='${esc(JSON.stringify({ kind: 'RESOLVE_HOLD', ticket_id: held.ticket_id }))}'>${icon('check')} Release ticket</button>
        <button class="btn" data-kind="hold" data-act='${esc(JSON.stringify({ kind: 'REMAKE', ticket_id: held.ticket_id }))}'>${icon('arrow-counter-clockwise')} Remake</button></div>
        <div class="disclaimer">Only a person releases a hold. The system never does.</div>`;
      return;
    }
    el.dataset.tier = String(a.tier);
    const pending = a.required_actions.filter((r) => r.carrier_id && a.blocking_carriers.includes(r.carrier_id));
    const assertAll = (claim, label, kind) => pending.length
      ? `<button class="btn" data-kind="${kind}" data-act='${esc(JSON.stringify({ kind: claim, alert_id: a.alert_id, carrier_ids: [...new Set(pending.map((r) => r.carrier_id))] }))}'>${icon('check')} ${label}</button>` : '';
    const dismiss = `<button class="btn" data-kind="quiet" data-act='${esc(JSON.stringify({ kind: 'DISMISS', alert_id: a.alert_id }))}'>${icon('x')} Dismiss</button>`;
    if (a.tier === 0) {
      const items = a.required_actions.map((r) => {
        const done = r.carrier_id ? !a.blocking_carriers.includes(r.carrier_id) : false;
        const flag = r.kind === 'USE_SEALED_BACKUP';
        return `
        <li data-done="${done ? 1 : 0}" class="${flag ? 'flag' : ''}">
          <span class="box">${done ? icon('check') : flag ? icon('warning') : ''}</span>
          ${icon(ACTION_ICON[r.kind] || 'square')} ${esc(r.label)}
          ${!done && r.carrier_id && ASSERT_LABEL[r.kind] ? `<button class="btn small" data-kind="quiet" data-act='${esc(JSON.stringify({ kind: 'ASSERT_REPLACED', alert_id: a.alert_id, carrier_ids: [r.carrier_id] }))}'>${ASSERT_LABEL[r.kind]}</button>` : ''}
        </li>`;
      }).join('');
      el.innerHTML = `<div class="label micro">Tier 0 · Reset prompt · Ticket ${esc(a.ticket_id)} · before you start</div>
        <div><h1 class="headline">${esc(a.headline)}</h1><ul class="checklist">${items}</ul></div>
        <div class="actions">${assertAll('ASSERT_REPLACED', 'All done — station reset', 'primary')}${dismiss}</div>`;
    } else if (a.tier === 1) {
      const first = a.required_actions[0];
      el.innerHTML = `<div class="label micro">Tier 1 · Interrupt · Ticket ${esc(a.ticket_id)}</div>
        <div><h1 class="headline">${esc(a.headline)}</h1>${a.body ? `<div class="body">${esc(a.body)}</div>` : ''}</div>
        <div class="actions">
          <button class="btn" data-kind="primary" data-act='${esc(JSON.stringify({ kind: 'ACKNOWLEDGE', alert_id: a.alert_id }))}'>${icon('arrows-clockwise')} ${esc(first ? first.label : 'On it')}</button>
          ${assertAll('ASSERT_REPLACED', 'Already swapped', 'quiet')}${dismiss}</div>`;
    } else {
      const implicated = [...new Set(a.required_actions.filter((r) => r.carrier_id).map((r) => r.carrier_id))];
      el.innerHTML = `<div class="label micro">Tier 2 · Hold at the pass · Ticket ${esc(a.ticket_id)}</div>
        <div><h1 class="headline">${esc(a.headline)}</h1>${a.body ? `<div class="body">${esc(a.body)}</div>` : ''}<div class="trace">${traceLines(a.derivation)}</div></div>
        <div class="actions">
          ${implicated.length ? `<button class="btn" data-kind="primary" data-act='${esc(JSON.stringify({ kind: 'ASSERT_CLEAN', alert_id: a.alert_id, carrier_ids: implicated }))}'>${icon('check')} Cook confirms ${esc(implicated.join(', '))} was clean</button>` : ''}
          <button class="btn" data-kind="hold" data-act='${esc(JSON.stringify({ kind: 'REMAKE', ticket_id: a.ticket_id, alert_id: a.alert_id }))}'>${icon('arrow-counter-clockwise')} Remake</button></div>
        <div class="disclaimer">This is an observation, not a determination. Confirm with the cook.</div>`;
    }
  }

  function kv(rows) { return `<table class="kv">${rows.map((r) => `<tr>${r.map((c, i) => `<td class="${i ? 'mono' : ''}">${c}</td>`).join('')}</tr>`).join('')}</table>`; }
  function renderInspector(s) {
    const ss = s.state_summary, rt = s.runtime;
    $('mode-now').textContent = ss.mode;
    $('carriers-table').innerHTML = `<table class="kv"><tr><th>carrier</th><th>kind</th><th>epistemic</th><th>seen</th><th>taints (grade · hops · via · event)</th></tr>${[...ss.carriers].sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind]).map((c) => `<tr><td class="mono">${esc(c.carrier_id)}</td><td>${c.kind}</td><td class="mono">${c.epistemic}</td><td class="mono">${fmtT(c.last_observed_at)}</td><td class="mono">${Object.values(c.taints).map((t) => `${esc(t.allergen_id)} ${GRADE_ABBR[t.grade]} h${t.hops} ← ${esc(t.source_carrier_id)} (${esc(t.source_event_id)})`).join('<br>') || '—'}</td></tr>`).join('')}</table>`;
    $('zones-count').textContent = rt.zones.length;
    $('zones-table').innerHTML = `<table class="kv"><tr><th>zone</th><th>kind</th><th>contents</th><th>carrier</th><th>last contact</th></tr>${rt.zones.map((z) => `<tr><td class="mono">${esc(z.zone_id)}</td><td>${z.kind}</td><td>${esc(z.contents.join(', ')) || '—'}</td><td class="mono">${esc(z.bound_carrier || '—')}</td><td class="mono">${fmtT(z.last_contact_at)}</td></tr>`).join('')}</table>`;
    const h = rt.health;
    $('health-table').innerHTML = kv([['mode', ss.mode], ['vision', h.vision], ['reasoning', h.reasoning], ['late rate', `${(h.late_rate * 100).toFixed(1)}%`], ['rejected events', h.rejected_events], ['last incident', esc(h.last_incident_event_id || '—')], ['message', esc(h.message || '—')], ['config / knowledge', `v${ss.config_version} / v${ss.knowledge_version}`], ['checksums', `${rt.config_checksum.slice(0, 12)} / ${rt.knowledge_checksum.slice(0, 12)}`], ['seq', rt.seq], ['time', `${fmtT(now())} (${rt.time.kind})`], ['conditions', esc(ss.conditions.join(', ') || '—')]]);
    const sc = $('scrub');
    const max = rt.recent_events.length ? rt.recent_events[rt.recent_events.length - 1].seq : 0;
    const atEnd = Number(sc.value) >= Number(sc.max);
    sc.max = max; if (atEnd) sc.value = max;
    $('scrub-val').textContent = sc.value;
    renderLog(s, Number(sc.value));
  }

  function render(s) {
    snap = s;
    renderTop(s); renderTickets(s); renderRisk(s);
    if (page === 'worker') { renderLog(s); renderGrid(s); renderSurface(s); }
    else renderInspector(s);
  }
  if (page === 'inspector') $('scrub').addEventListener('input', () => { if (snap) { $('scrub-val').textContent = $('scrub').value; renderLog(snap, Number($('scrub').value)); } });

  const params = new URLSearchParams(location.search);
  if (params.get('mock')) {
    fetch('/static/mock/snapshot.example.json').then((r) => r.json()).then(render);
    return;
  }
  function connect() {
    const ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`);
    ws.onmessage = (m) => render(JSON.parse(m.data));
    ws.onclose = () => { $('banner').dataset.mode = 'DOWN'; $('banner-text').textContent = 'DISPLAY DISCONNECTED'; setTimeout(connect, 1000); };
  }
  connect();
})();
