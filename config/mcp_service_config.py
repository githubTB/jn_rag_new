"""
config/mcp_service_config.py — 服务配置

统一管理服务名称和中文名称的映射关系。
"""

# 服务名称到中文名称的映射
SERVICE_CN_NAME_BY_NAME: dict[str, str] = {
    "base_extract_prompt_template": "企业基本信息",
    "product_extract_prompt_template": "近三年产品产量产值情况",
    "process_flow_extract_prompt_template": "生产工艺流程",
    "major_production_equipment_extract_prompt_template": "主要生产设备信息",
    "transformer_efficiency_benchmark_extract_prompt_template": "变压器设备能效对标",
    "air_compressor_efficiency_benchmark_extract_prompt_template": "空压机设备能效对标",
    "chiller_efficiency_benchmark_extract_prompt_template": "冷水机组设备能效对标",
    "motor_efficiency_benchmark_extract_prompt_template": "电动机设备能效对标",
    "energy_metering_instrument_extract_prompt_template": "能源计量器具信息",
    "management_system_status_extract_prompt_template": "管理体系现状",
    "energy_extract_prompt_template": "近三年能源消耗",
    "raw_material_consumption_extract_prompt_template": "主要原辅材料消耗",
    "material_composition_extract_prompt_template": "原辅材料主要成分",
    "water_extract_prompt_template": "近三年用水情况",
    "waste_gas_treatment_extract_prompt_template": "废气治理设施",
    "waste_gas_emission_total_extract_prompt_template": "废气污染物排放情况",
    "wastewater_pollutants_extract_prompt_template": "废水污染物",
    "solid_waste_generation_disposal_extract_prompt_template": "近三年固体废物产生与处置",
    "noise_monitoring_extract_prompt_template": "厂界环境噪声",
    "greenhouse_gas_emissions_extract_prompt_template": "温室气体排放",
    "land_intensification_extract_prompt_template": "用地集约化信息",
    "green_material_usage_extract_prompt_template": "绿色物料使用",
    "pollutant_emission_per_product_extract_prompt_template": "单位产品与产值主要污染物排放情况",
    "gas_emission_per_product_extract_prompt_template": "单位产品与产值主要废气排放情况",
    "wastewater_emission_per_product_extract_prompt_template": "单位产品与产值主要废水排放情况",
    "raw_material_consumption_per_product_extract_prompt_template": "单位产品与产值主要原材料消耗",
    "water_consumption_per_product_extract_prompt_template": "单位产品与产值水耗",
    "energy_consumption_per_product_extract_prompt_template": "单位产品与产值综合能耗",
    "carbon_emission_per_product_extract_prompt_template": "单位产品与产值主要碳排放情况",
    "qualification_certificate_info_extract_prompt_template": "资质证书信息"
}
