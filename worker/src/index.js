/**
 * Optional Cloudflare Worker: BoE IUDBEDR CSV → JSON for TRMNL polling.
 * Deploy with `npx wrangler deploy` from worker/. Point polling_url at the Worker.
 */
const CSV_URL =
  "https://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=01/Jan/2020&Dateto=now&SeriesCodes=IUDBEDR&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N";

function parse(csv) {
  const rows = [];
  for (const line of csv.split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.toUpperCase().startsWith("DATE")) continue;
    const [date, rateS] = t.split(",").map((s) => s.trim());
    const rate = parseFloat(rateS);
    if (date && !Number.isNaN(rate)) rows.push({ date, rate });
  }
  const changes = [];
  let prev = null;
  for (const row of rows) {
    if (prev && row.rate !== prev.rate) {
      changes.push({
        date: row.date,
        rate: row.rate,
        previous: prev.rate,
        delta: +(row.rate - prev.rate).toFixed(4),
      });
    }
    prev = row;
  }
  const current = prev;
  const last = changes[changes.length - 1] || null;
  return {
    current: current?.rate ?? null,
    current_pct: current ? current.rate.toFixed(2) : null,
    current_date: current?.date ?? null,
    previous: last?.previous ?? current?.rate ?? null,
    previous_pct: (last?.previous ?? current?.rate)?.toFixed?.(2) ?? null,
    last_change_date: last?.date ?? current?.date ?? null,
    delta: last?.delta ?? 0,
    delta_pct: last ? (last.delta >= 0 ? "+" : "") + last.delta.toFixed(2) : "0.00",
    history: changes.slice(-8).reverse(),
    observation_count: rows.length,
    source: "IUDBEDR",
  };
}

export default {
  async fetch() {
    const res = await fetch(CSV_URL, {
      headers: { "User-Agent": "trmnl-boe-worker/1.0" },
    });
    if (!res.ok) {
      return Response.json({ error: "upstream", status: res.status }, { status: 502 });
    }
    const csv = await res.text();
    return Response.json(parse(csv), {
      headers: { "Cache-Control": "public, max-age=3600" },
    });
  },
};
