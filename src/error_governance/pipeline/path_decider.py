"""Step 09: 实施路径判定 — DOC-03"""

from error_governance.models.diagnosis_result import ImplementationPath, ExperienceSeverity


def decide(features, experience) -> tuple[ImplementationPath, str]:
    major = features.major_category

    if major == "系统异常类":
        return ImplementationPath.D_BACKEND, "涉及后端服务/基础设施，需后端改造"
    if "校验" in major or "权限" in major:
        if experience.form_severity != ExperienceSeverity.CRITICAL:
            return ImplementationPath.C_FRONTEND, "需调整前端校验时机和提示形式"
        return ImplementationPath.D_BACKEND, "需前后端协同"
    return ImplementationPath.A_COPY, "问题以文案和引导为主，可走文案发布路径"
