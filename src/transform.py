
"""Parse BoE IADB CSV (IUDBEDR) into current/previous/history for Liquid."""


def run(input):
    # CSV may arrive as raw string, {data: "..."}, or already-parsed rows
    raw = input.get("data") if isinstance(input, dict) else input
    if isinstance(raw, dict) and "data" in raw:
        raw = raw["data"]

    rows = []
    if isinstance(raw, list):
        # Platform-parsed CSV → list of dicts or list of lists
        for item in raw:
            if isinstance(item, dict):
                date = item.get("DATE") or item.get("Date") or item.get("date") or next(iter(item.values()), None)
                # find rate value
                rate = None
                for k, v in item.items():
                    if str(k).upper() in ("DATE", "DATE "):
                        continue
                    rate = v
                    break
                if date is not None and rate is not None:
                    rows.append((str(date).strip(), str(rate).strip()))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                rows.append((str(item[0]).strip(), str(item[1]).strip()))
    else:
        text = raw if isinstance(raw, str) else str(raw or "")
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            line = line.strip()
            if not line or line.upper().startswith("DATE"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 2:
                rows.append((parts[0], parts[1]))

    # Chronological daily observations → change events
    history_changes = []
    prev_rate = None
    prev_date = None
    for date, rate_s in rows:
        try:
            rate = float(rate_s)
        except ValueError:
            continue
        if prev_rate is None:
            prev_rate = rate
            prev_date = date
            continue
        if rate != prev_rate:
            history_changes.append({
                "date": date,
                "rate": rate,
                "previous": prev_rate,
                "delta": round(rate - prev_rate, 4),
            })
            prev_rate = rate
            prev_date = date
        else:
            prev_date = date
            prev_rate = rate

    current = prev_rate
    current_date = prev_date
    last_change = history_changes[-1] if history_changes else None
    previous_rate = last_change["previous"] if last_change else current
    last_change_date = last_change["date"] if last_change else current_date
    delta = last_change["delta"] if last_change else 0

    # Show newest changes first, limited
    recent = list(reversed(history_changes[-8:]))

    return {
        "current": current,
        "current_pct": f"{current:.2f}" if current is not None else "—",
        "current_date": current_date or "",
        "previous": previous_rate,
        "previous_pct": f"{previous_rate:.2f}" if previous_rate is not None else "—",
        "last_change_date": last_change_date or "",
        "delta": delta,
        "delta_pct": f"{delta:+.2f}" if delta is not None else "—",
        "history": recent,
        "observation_count": len(rows),
    }
