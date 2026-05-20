"""DOC-01 报错特征分类 — 基于规则的关键词匹配 + 决策树"""

from error_diagnosis.models import ErrorInput, ErrorFeatures

# ── 分类决策树（DOC-01 Section 3）─────────────────

def classify_error(input: ErrorInput) -> ErrorFeatures:
    """按 DOC-01 决策流程归类，返回 ErrorFeatures"""
    text = input.error_message

    # Step 1: 系统技术问题？
    if _match_any(text, ["Network Error", "timeout", "ECONNABORTED", "500", "502", "504"]):
        return _build("系统异常类", "网络/超时错误", "网络请求", "请求是否成功到达后端", "网络断开/超时/服务器错误")
    if _match_any(text, ["token", "session", "签名", "登录态", "登录已失效"]):
        return _build("权限类", "登录/会话失效", "任何需要登录态的操作", "校验 token/session 有效性", "未登录/token 为空/签名过期")
    if _match_any(text, ["远程服务", "接口调用异常", "RPC"]):
        return _build("系统异常类", "远程调用/接口异常", "调用外部/微服务接口", "RPC/HTTP 调用是否成功", "远程服务超时/不可用")

    if _match_any(text, ["服务异常", "系统繁忙", "服务维护", "系统异常"]):
        return _build("系统异常类", "服务端通用异常", "后端操作", "后端服务是否正常响应", "服务异常/系统繁忙")

    # Step 2: 用户身份/授权？
    if _match_any(text, ["权限", "无访问", "管理员", "授权", "没有.*权限"]):
        if _match_any(text, ["数据权限", "部门", "账套", "区域", "数据范围"]):
            return _build("权限类", "数据权限不足", "查看/操作特定数据范围", "校验用户数据范围权限", "未被授予该数据范围权限")
        return _build("权限类", "操作权限不足", "执行某功能操作", "校验功能/接口操作权限码", "未分配该功能权限")

    # Step 3: 数据校验？
    if _match_any(text, ["不能为空", "必填"]):
        return _build("数据校验类", "参数为空校验", "表单提交/数据保存", "校验必填字段是否为空", "必填字段未填写")
    if _match_any(text, ["格式不正确", "长度超过", "不合法", "格式错误"]):
        return _build("数据校验类", "参数格式/内容错误", "表单提交/数据导入", "校验字段值格式", "格式错误/编码规则不符/字段超长")
    if _match_any(text, ["已存在", "重复"]):
        return _build("数据校验类", "唯一性/重复校验", "新增/创建数据", "校验名称/编码是否重复", "提交数据与已有数据重复")
    if _match_any(text, ["文件", "上传", "导入", "解析失败", "模板"]):
        return _build("数据校验类", "文件上传校验", "文件上传/导入", "校验文件格式/大小/名称/内容", "文件格式不支持/过大/解析失败")
    if _match_any(text, ["金额", "税额", "数值", "勾稽", "不等于", "不能为0"]):
        return _build("数据校验类", "金额/数值校验", "财务开票/薪资计算/凭证录入", "金额勾稽关系/数值转换校验", "金额不一致/非数值/为0")

    # Step 4: 数据生命周期状态？
    if _match_any(text, ["不存在", "已被删除", "未找到", "已删除"]):
        return _build("业务状态类", "数据/记录不存在", "查看/操作具体数据记录", "根据 ID 查询记录是否存在", "数据已被删除/作废/从未创建")
    if _match_any(text, ["已处理", "请勿重复", "已结束"]):
        return _build("业务状态类", "重复操作/已处理", "审批/任务处理/确认", "校验是否已处于终态", "任务已被他人处理/流程已结束")
    if _match_any(text, ["锁定", "结账", "冻结", "不可修改"]):
        return _build("业务状态类", "已锁定/已冻结/已结账", "修改/编辑已锁定数据", "校验数据锁定/结账状态", "数据被锁定不可修改")
    if _match_any(text, ["流程中", "审批中", "处理中", "进行中"]):
        return _build("业务状态类", "流程中/处理中", "对流程中数据发起新操作", "校验是否有进行中流程", "数据处于审批中/计算中")
    if _match_any(text, ["不允许", "不能", "不可进行操作"]):
        return _build("业务状态类", "状态不允许操作", "执行状态变更操作", "状态机校验", "当前状态不在允许操作列表")

    # Step 5: 特定业务领域？
    if _match_any(text, ["考勤", "排班", "打卡", "请假", "调店"]):
        return _build("业务规则限制类", "考勤相关", "考勤操作", "考勤周期/排班/时间冲突校验", "考勤周期未设置/时间冲突")
    if _match_any(text, ["薪资", "算税", "个税", "工资单", "薪酬"]):
        return _build("业务规则限制类", "薪资/算税相关", "薪资计算/个税申报", "薪资组状态/算税状态校验", "薪资组锁定/算税中/已申报")
    if _match_any(text, ["发票", "税局", "税号", "开票"]):
        return _build("业务规则限制类", "发票/税务相关", "发票开具/税局登录", "发票信息完整性/税局接口校验", "发票不匹配/税局登录失败")
    if _match_any(text, ["凭证", "账套", "科目", "借贷"]):
        return _build("业务规则限制类", "财务凭证相关", "凭证录入/账套管理", "凭证编号唯一性/结账状态校验", "凭证重复/账套不存在")

    # 未命中
    return _build("未分类", "未分类", "未知", "未知", "未知")


def _match_any(text: str, keywords: list[str]) -> bool:
    """任意关键词命中则返回 True"""
    import re
    for kw in keywords:
        if re.search(kw, text, re.IGNORECASE):
            return True
    return False


def _build(major: str, minor: str, task: str, validation: str, reason: str) -> ErrorFeatures:
    """构建 ErrorFeatures"""
    return ErrorFeatures(
        major_category=major,
        minor_category=minor,
        task_type=task,
        validation_logic=validation,
        error_reason=reason,
        business_module=_infer_module(minor),
        search_keywords=_extract_keywords(minor, reason),
    )


def _infer_module(minor: str) -> str:
    mapping = {
        "考勤": "考勤管理", "薪资": "薪资计算", "算税": "薪资计算",
        "财务": "财务管理", "凭证": "财务管理", "发票": "发票税务",
        "权限": "权限管理", "登录": "权限管理",
        "文件上传": "通用", "参数为空": "通用", "格式": "通用", "唯一性": "通用",
        "金额": "财务管理", "网络": "系统底层",
    }
    for k, v in mapping.items():
        if k in minor:
            return v
    return "通用业务"


def _extract_keywords(minor: str, reason: str) -> list[str]:
    """从报错特征中提取检索关键词"""
    return [minor, reason] if reason and reason != "未知" else [minor]
