from typing import Optional
from sqlalchemy.orm import Session
from app.models.tables import UserMapping


class IdentityService:
    def __init__(self, db: Session):
        self.db = db

    def get_platform_user_id(self, feishu_user_id: str, platform: str) -> Optional[str]:
        """Look up platform user ID from Feishu user ID"""
        mapping = self.db.query(UserMapping).filter(
            UserMapping.feishu_user_id == feishu_user_id
        ).first()
        if not mapping:
            return None

        if platform == "dingtalk":
            return mapping.dingtalk_user_id
        elif platform == "wecom":
            return mapping.wecom_user_id
        return None

    def get_feishu_user_id(self, platform_user_id: str, platform: str) -> Optional[str]:
        """Look up Feishu user ID from platform user ID"""
        if platform == "dingtalk":
            mapping = self.db.query(UserMapping).filter(
                UserMapping.dingtalk_user_id == platform_user_id
            ).first()
        elif platform == "wecom":
            mapping = self.db.query(UserMapping).filter(
                UserMapping.wecom_user_id == platform_user_id
            ).first()
        else:
            return None

        return mapping.feishu_user_id if mapping else None

    def auto_match(self) -> int:
        """Match users by phone number across platforms"""
        # Find all records with phone numbers but missing cross-platform IDs
        # Group by phone, merge mappings
        matched = 0
        mappings = self.db.query(UserMapping).filter(UserMapping.phone.isnot(None)).all()

        phone_groups: dict[str, list[UserMapping]] = {}
        for m in mappings:
            if m.phone not in phone_groups:
                phone_groups[m.phone] = []
            phone_groups[m.phone].append(m)

        for phone, group in phone_groups.items():
            if len(group) < 2:
                continue

            # Merge: find feishu and dingtalk users
            feishu_id = next((m.feishu_user_id for m in group if m.feishu_user_id), None)
            dingtalk_id = next((m.dingtalk_user_id for m in group if m.dingtalk_user_id), None)
            wecom_id = next((m.wecom_user_id for m in group if m.wecom_user_id), None)
            name = next((m.name for m in group if m.name), None)

            if feishu_id and dingtalk_id:
                # Update first record with complete mapping, delete duplicates
                primary = group[0]
                primary.feishu_user_id = feishu_id
                primary.dingtalk_user_id = dingtalk_id
                primary.wecom_user_id = wecom_id
                primary.name = name

                for duplicate in group[1:]:
                    self.db.delete(duplicate)

                matched += 1

        self.db.commit()
        return matched

    # Stub methods for P1
    def sync_from_feishu(self) -> int:
        """Pull Feishu contacts - stub for P1"""
        return 0

    def sync_from_dingtalk(self) -> int:
        """Pull DingTalk contacts - stub for P1"""
        return 0
