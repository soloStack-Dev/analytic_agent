          USER
           │
           │ Prompt + Excel/JSON
           ▼
       ┌─────────┐
       │  HTMX   │
       └────┬────┘
            │
            ▼
       ┌─────────┐
       │ FastAPI │
       └────┬────┘
            │
            ▼
       ┌──────────┐
       │  Pandas  │──────► Dataset schema/statistics
       └────┬─────┘                    │
            │                          ▼
            │                    ┌───────────┐
            └───────────────────►│ LangGraph │
                                 │   Agent   │
                                 └─────┬─────┘
                                       │
                                  Chart Plan
                                       │
                                       ▼
                               ┌──────────────┐
                               │ Validation   │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │    Pandas    │
                               │   Analysis   │
                               └──────┬───────┘
                                      │
                                      ▼
                               ┌──────────────┐
                               │  Matplotlib  │
                               └──────┬───────┘
                                      │
                                  PNG/SVG
                                      │
                                      ▼
                                    HTMX
                                      │
                                      ▼
                              📊 Chart + Analysis