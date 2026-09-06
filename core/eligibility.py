"""
core/eligibility.py
Pillar 2 — هل تستحق؟ (Do You Qualify?)
A deterministic, zero-LLM decision guide pointing citizens to official social-protection programs.
Guarantees zero PII storage and zero automated eligibility verdicts.
"""

import os
import yaml
from typing import Dict, Any, Optional

TREE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "eligibility_tree.yaml")


class EligibilityEngine:
    def __init__(self, tree_path: str = TREE_PATH):
        self.tree_path = tree_path
        self.tree: Dict[str, Any] = self._load_tree()

    def _load_tree(self) -> Dict[str, Any]:
        if not os.path.exists(self.tree_path):
            return {}
        with open(self.tree_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def get_node(self, node_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves a node from the decision tree. Defaults to 'start'.
        """
        if not node_id or node_id not in self.tree:
            node_id = "start"

        node_data = self.tree.get(node_id, {})
        
        if node_id == "start":
            return {
                "node_id": "start",
                "message": node_data.get("message_ar", ""),
                "options": [
                    {"id": opt["id"], "label": opt["label_ar"], "goto": opt["goto"]}
                    for opt in node_data.get("options", [])
                ],
                "is_leaf": False
            }

        # Leaf node with official program information
        return {
            "node_id": node_id,
            "title": node_data.get("title_ar", ""),
            "info": node_data.get("info_ar", ""),
            "action": node_data.get("action_ar", ""),
            "official_channel": node_data.get("official_channel", ""),
            "disclaimer": node_data.get("disclaimer_ar", "ℹ️ دي معلومة استرشادية — القرار النهائي بيكون من الجهة الرسمية."),
            "is_leaf": True
        }

    def format_node_reply(self, node_id: str) -> str:
        """
        Formats a complete Egyptian Arabic response message for a node.
        """
        data = self.get_node(node_id)
        if data["node_id"] == "start":
            reply = f"{data['message']}\n\n"
            for i, opt in enumerate(data.get("options", [])):
                reply += f"{i+1}. {opt['label']}\n"
            return reply.strip()

        reply = (
            f"📌 *{data.get('title', '')}*\n\n"
            f"{data.get('info', '')}\n\n"
            f"🚀 *خطوات التقديم والاستعلام:*\n{data.get('action', '')}\n\n"
            f"🏛 *الجهة والقناة الرسمية:*\n{data.get('official_channel', '')}\n\n"
            f"_{data.get('disclaimer', '')}_"
        )
        return reply
