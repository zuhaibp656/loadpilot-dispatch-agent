# LoadPilot test prompts (Gemini Enterprise / adk web)

Sample files: `app/data/samples/` in the repo, and in GCS at
`https://storage.cloud.google.com/zuhaibp-ai-loadpilot-media/demo-data/samples/<file>`.
Download them to your phone or laptop, then attach them in the Gemini Enterprise chat.

Demo data explorer: https://storage.cloud.google.com/zuhaibp-ai-loadpilot-media/demo-data/loadpilot_demo_data.html
BigQuery dataset: `zuhaibp-ai.loadpilot_demo` (13 tables: stores, orders, cartons, skus, truck_types, fleet, drivers, driver_runs, ...)

---

## 1. Fleet manager (plans the whole DC)

| # | Prompt | Attach | What you should see |
|---|--------|--------|---------------------|
| F1 | `Plan today's dispatch from Bhiwandi DC` | – | The fleet plan (10 trucks consolidated to about 8), a Today vs LoadPilot table, the route map and 3D load |
| F2 | `Open the planning form` | – | A wizard with truck types (3–5), counts, shift start and corridor |
| F3 | `Use 4 T14 and 3 T17 trucks, shift starts 06:30, re-plan` | – | A re-plan using that fleet mix |
| F4 | `Show the load plan for T17-1` | – | One truck's LIFO sequence and a table of where each carton goes |
| F5 | `Ravi says he has been given the West route. Is that right?` | – | A check of the corridor claim, which branches into a confirmation or an alternative |
| F6 | `Here are today's orders, plan the trucks` | `orders_today.csv`, `orders_today.xlsx`, `orders_today.pdf` or `orders_email.txt` | Orders ingested from the file, then a plan |
| F7 | `These cartons are staged for store S003, add them` | `cartons_S003_staging.jpg` | Labels read from the photo and attached to S003 |
| F8 | `Read this dock photo` | `cartons_mixed_dock.jpg`, `label_closeup.png` | Cartons grouped by store |

## 2. Fleet manager → individual driver instructions

| # | Prompt | What you should see |
|---|--------|---------------------|
| M1 | `Send each driver his individual instructions` | One `####` block per driver (route, drops, where each store's cartons sit in the truck) plus a personal link for each driver |
| M2 | `Give Suresh his briefing only` | A single-driver page |

## 3. Driver (one person, one truck)

| # | Prompt | Attach | What you should see |
|---|--------|--------|---------------------|
| D1 | `I'm Suresh, plan my day and show me how to load my truck` | – | "Your route today": 6 drops, 107 cartons, about 149 km, plus 3D loading |
| D2 | `Here are my cartons, where do they go?` | `driver_suresh_t14_north_cartons_a.jpg` + `_b.jpg` | Stores read from the photos, then his route and 3D load |
| D3 | `I'm Ravi, these are my boxes, I drive a T17` | `driver_ravi_t17_west_cartons_a.jpg` + `_b.jpg` | Ravi's West run (8 drops) |
| D4 | `I'm Imran with a pickup, here are my cartons` | `driver_imran_pkp_south_cartons_a.jpg` + `_b.jpg` | Imran's South pickup run (6 drops) |
| D5 | `My stops are S006, S007, S008, S009, S010, S011. I drive a T14` | – | A route built from the stop ids you typed |
| D6 | Paste the text of `driver_suresh_t14_north_orders.txt` (the WhatsApp message from the dispatch manager) | – | Stops parsed from the chat, then his route |

## 4. Using the interactive view

- **Route map**: click a numbered stop to see its ETA, cartons and time window.
  The **"📦 Where are these cartons in the truck?"** button jumps to the 3D view with that store highlighted.
- **3D truck loading**: click a store in the right-hand list.
  - The other cartons fade out.
  - The floor footprint is marked "Stop N · a–b cm from door".
  - A card shows where to put the cartons, the load steps and the goods.
- Hover a carton for its details; click a carton to pin its store. Drag to rotate. **Show all stores** resets the view.
