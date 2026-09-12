from datetime import date, timedelta

def add_task(tasks, subject, name, deadline, priority, hours_needed):
    tasks.append({
        "subject": subject, "name": name, "deadline": deadline,
        "priority": priority, "hours_needed": float(hours_needed),
        "hours_done": 0.0, "done": False
    })

def priority_label(priority):
    if priority >= 4:
        return "ðŸ”¥ High", "high"
    if priority == 3:
        return "âš¡ Medium", "medium"
    return "ðŸŒ± Low", "low"

def days_left_text(deadline):
    d = (deadline - date.today()).days
    if d < 0: return f"âš ï¸ Overdue by {abs(d)}d"
    if d == 0: return "â° Due TODAY"
    if d == 1: return "â° Due tomorrow"
    return f"ðŸ“… {d} days left"

def urgency(task, day):
    days = max((task["deadline"] - day).days, 1)
    remaining = max(task["hours_needed"] - task["hours_done"], 0)
    return (task["priority"] * 10 * max(remaining, .1)) / days

def generate_schedule(tasks, daily_hours, days_ahead=7):
    active = [t for t in tasks if not t["done"] and t["deadline"] >= date.today()]
    remaining = {id(t): t["hours_needed"] - t["hours_done"] for t in active}
    result = {}
    for offset in range(days_ahead):
        day = date.today() + timedelta(days=offset)
        available = float(daily_hours)
        day_items = []
        ranked = sorted(active, key=lambda t: urgency(t, day), reverse=True)
        for t in ranked:
            if available <= 0 or t["deadline"] < day: continue
            left = remaining[id(t)]
            amount = min(left, available, 2)
            if amount > 0:
                day_items.append((t["subject"], t["name"], amount, t["priority"]))
                remaining[id(t)] -= amount
                available -= amount
        result[day] = day_items
    return result
