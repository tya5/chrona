"""Reproduce issue #1298's published scale generator without global RNG state."""
from datetime import date, timedelta
from random import Random


def routing_scale_project(item_count: int, *, dependencies: bool = True) -> dict:
    random = Random(7)
    origin = date(2027, 1, 4)
    objects, relations = {}, []
    for group in range(max(1, item_count // 20)):
        group_id = f"g{group:03d}"
        objects[group_id] = {"type": "group", "title": f"Workstream {group}",
                             "schedule": {"mode": "rollup"}}
        previous, previous_start = None, None
        for child in range(19):
            if len(objects) >= item_count:
                break
            object_id = f"t{group:03d}-{child:02d}"
            start = origin + timedelta(days=random.randint(0, 330))
            if child % 6 == 5:
                objects[object_id] = {
                    "type": "gate", "title": f"Gate {group}.{child}", "parent": group_id,
                    "schedule": {"mode": "fixed-point", "at": start.isoformat()},
                }
            else:
                end = start + timedelta(days=random.randint(3, 40))
                objects[object_id] = {
                    "type": "task", "title": f"Task {group}.{child} work package", "parent": group_id,
                    "schedule": {"mode": "fixed-span", "start": start.isoformat(), "end": end.isoformat()},
                }
                if (dependencies and previous is not None and previous_start <= start
                        and random.random() < 0.6):
                    relations.append({
                        "id": f"r-{object_id}", "type": "dependency",
                        "from": {"object": previous, "endpoint": "start"},
                        "to": {"object": object_id, "endpoint": "start"}, "lag": "0d",
                    })
                previous, previous_start = object_id, start
    return {"version": "timeline/v0.7",
            "project": {"id": f"scale-{item_count}", "title": f"Scale test {item_count} items"},
            "objects": objects, "relations": relations}
