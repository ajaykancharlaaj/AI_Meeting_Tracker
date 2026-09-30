"""
Simulated Multi-Meeting Evaluation Dataset with Ground Truth Annotations.

Features:
- 5 sequential meetings (M1, M2, M3, M4, M5)
- 5 realistic project roles/speakers (Daniel, Rahul, Priya, Maya, Leo)
- 22 multi-meeting dialogue segments
- Repeated tasks with natural semantic paraphrasing
- Explicit and qualitative progress tracking
- Changed deadlines ("moved to Monday")
- Blocked tasks and multi-tier dependency propagation
- Completed and reopened tasks
- Cross-meeting state contradictions
- Linguistic uncertainty markers
- Repeated unresolved stagnation
"""

from typing import Any, Dict, List

EVALUATION_MEETINGS = [
    # -------------------------------------------------------------
    # MEETING 1: Sprint Planning & Task Allocation
    # -------------------------------------------------------------
    {
        "meeting_id": "M1",
        "reference_date": "2026-09-01",
        "transcript": [
            {
                "segment_id": "M1-S01",
                "speaker": "Daniel",
                "start_time": "00:01:00",
                "text": "Rahul will develop the login module. It is due by September 20.",
            },
            {
                "segment_id": "M1-S02",
                "speaker": "Priya",
                "start_time": "00:02:15",
                "text": "I will create the payment API by September 15.",
            },
            {
                "segment_id": "M1-S03",
                "speaker": "Daniel",
                "start_time": "00:03:30",
                "text": "Maya, please turn those wireframes into the final dashboard design. You will own that task, and it is due by Friday, September 18.",
            },
            {
                "segment_id": "M1-S04",
                "speaker": "Leo",
                "start_time": "00:04:45",
                "text": "I will deploy the backend server by September 12.",
            },
            {
                "segment_id": "M1-S05",
                "speaker": "Rahul",
                "start_time": "00:06:00",
                "text": "Database indexing optimization has been assigned to Rahul.",
            }
        ]
    },

    # -------------------------------------------------------------
    # MEETING 2: Progress Check & Dependencies
    # -------------------------------------------------------------
    {
        "meeting_id": "M2",
        "reference_date": "2026-09-05",
        "transcript": [
            {
                "segment_id": "M2-S01",
                "speaker": "Rahul",
                "start_time": "00:02:10",
                "text": "The login functionality is around 50 percent done.",
            },
            {
                "segment_id": "M2-S02",
                "speaker": "Priya",
                "start_time": "00:03:40",
                "text": "The payment API is blocked because of banking gateway partner delays.",
            },
            {
                "segment_id": "M2-S03",
                "speaker": "Maya",
                "start_time": "00:05:00",
                "text": "Understood. The final design depends on Leo providing the updated brand assets first.",
            },
            {
                "segment_id": "M2-S04",
                "speaker": "Rahul",
                "start_time": "00:06:30",
                "text": "Database indexing optimization is still pending.",
            }
        ]
    },

    # -------------------------------------------------------------
    # MEETING 3: Blockers, Deadlines & Uncertainty
    # -------------------------------------------------------------
    {
        "meeting_id": "M3",
        "reference_date": "2026-09-10",
        "transcript": [
            {
                "segment_id": "M3-S01",
                "speaker": "Rahul",
                "start_time": "00:01:50",
                "text": "The login module is blocked because of the authentication API.",
            },
            {
                "segment_id": "M3-S02",
                "speaker": "Maya",
                "start_time": "00:03:15",
                "text": "The deadline moved to Monday for the dashboard design.",
            },
            {
                "segment_id": "M3-S03",
                "speaker": "Leo",
                "start_time": "00:04:40",
                "text": "The backend server is complete and live in staging.",
            },
            {
                "segment_id": "M3-S04",
                "speaker": "Rahul",
                "start_time": "00:06:00",
                "text": "Database indexing optimization is still pending review.",
            },
            {
                "segment_id": "M3-S05",
                "speaker": "Priya",
                "start_time": "00:07:20",
                "text": "I think the notification service is probably completed.",
            }
        ]
    },

    # -------------------------------------------------------------
    # MEETING 4: Resolution & Pre-Release
    # -------------------------------------------------------------
    {
        "meeting_id": "M4",
        "reference_date": "2026-09-15",
        "transcript": [
            {
                "segment_id": "M4-S01",
                "speaker": "Rahul",
                "start_time": "00:02:00",
                "text": "The login module has been completed.",
            },
            {
                "segment_id": "M4-S02",
                "speaker": "Maya",
                "start_time": "00:03:30",
                "text": "The final dashboard design is complete.",
            },
            {
                "segment_id": "M4-S03",
                "speaker": "Daniel",
                "start_time": "00:05:10",
                "text": "The payment API is completed and ready.",
            },
            {
                "segment_id": "M4-S04",
                "speaker": "Rahul",
                "start_time": "00:07:00",
                "text": "Database indexing optimization is still pending.",
            }
        ]
    },

    # -------------------------------------------------------------
    # MEETING 5: Post-Release & Contradiction/Reopen Sync
    # -------------------------------------------------------------
    {
        "meeting_id": "M5",
        "reference_date": "2026-09-22",
        "transcript": [
            {
                "segment_id": "M5-S01",
                "speaker": "Priya",
                "start_time": "00:02:15",
                "text": "The payment API is still incomplete because of webhook failures.",
            },
            {
                "segment_id": "M5-S02",
                "speaker": "Maya",
                "start_time": "00:04:30",
                "text": "The dashboard design was reopened because of mobile responsiveness bugs.",
            },
            {
                "segment_id": "M5-S03",
                "speaker": "Daniel",
                "start_time": "00:06:00",
                "text": "That is our decision to prioritize the dashboard bugfix.",
            }
        ]
    }
]

# Ground truth annotations for quantitative evaluation
GROUND_TRUTH = {
    # Task entity resolutions across meetings
    "entity_resolution_pairs": [
        ("M2-S01", "login functionality", "develop login module", True),
        ("M3-S01", "login module", "develop login module", True),
        ("M4-S01", "login module", "develop login module", True),
        ("M3-S02", "dashboard design", "turn those wireframes into the final dashboard design", True),
        ("M4-S02", "final dashboard design", "turn those wireframes into the final dashboard design", True),
        ("M5-S02", "dashboard design", "turn those wireframes into the final dashboard design", True),
        ("M4-S03", "payment API", "create the payment API", True),
        ("M5-S01", "payment API", "create the payment API", True),
    ],

    # State sequence expectations
    "task_state_sequences": {
        "login_module": ["ASSIGNED", "IN_PROGRESS", "BLOCKED", "COMPLETED"],
        "dashboard_design": ["ASSIGNED", "IN_PROGRESS", "COMPLETED", "REOPENED"],
        "payment_api": ["ASSIGNED", "BLOCKED", "COMPLETED", "INCOMPLETE"],
        "backend_deploy": ["ASSIGNED", "COMPLETED"],
    },

    # Final current state ground truth after Meeting 5
    "final_states": {
        "login_module": "COMPLETED",
        "dashboard_design": "REOPENED",
        "backend_deploy": "COMPLETED",
    },

    # Contradiction ground truth
    "expected_contradictions": [
        {
            "task_concept": "payment_api",
            "from_state": "COMPLETED",
            "to_state": "INCOMPLETE",
            "m_prev": "M4",
            "m_curr": "M5",
        }
    ],

    # Deadlines ground truth
    "deadline_changes": [
        {
            "task_concept": "dashboard_design",
            "initial_deadline": "2026-09-18",
            "new_deadline": "2026-09-21",
        }
    ],

    # Uncertainty statements ground truth
    "uncertain_segments": [
        ("M3-S05", True),  # "probably completed"
        ("M4-S01", False), # "has been completed"
    ],

    # Stagnant unresolved task
    "stagnant_tasks": [
        "Database indexing optimization"
    ]
}
