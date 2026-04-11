"""
green_report_chapters_config.py - 绿色生成水平报告章节配置文件

定义绿色生产水平报告的章节结构，支持最多5级目录。
章节编号格式：1, 1.1, 1.1.1, 1.1.1.1, 1.1.1.1.1

每个章节包含：
- chapter: 章节目录
- title: 章节标题
- description: 章节简介/描述
- keywords: 关键词列表
"""

from typing import TypedDict


class ChapterNode(TypedDict, total=False):
    """章节节点"""
    chapter: str  # 章节目录
    title: str  # 章节标题
    description: str  # 章节简介
    keywords: list[str]  # 关键词列表
    children: dict[str, "ChapterNode"]  # 子章节


GREEN_REPORT_CHAPTERS: dict[str, ChapterNode] = {
    "1": {
        "chapter": "1",
        "title": "企业基本情况",
        "description": "企业基本信息和绿色生产管理现状",
        "keywords": ["企业概况", "基本信息", "生产工艺", "设备"],
        "children": {
            "1.1": {
                "chapter": "1.1",
                "title": "企业概况",
                "description": "企业基本信息、生产工艺流程和主要设备",
                "keywords": ["企业", "概况", "工艺", "设备"],
                "children": {
                    "1.1.1": {
                        "chapter": "1.1.1",
                        "title": "企业基本信息",
                        "description": "企业基本信息介绍",
                        "keywords": [
                            "基础信息类：企业全称、企业简称、成立年份、产能规模",
                            "产品技术类：产品类别，核心工艺 / 技术、核心产品",
                            "市场地位类：市场占有率 ，国际排名，相关行业",
                            "荣誉研发类：荣誉称号，研发平台 专利数量"
                        ],
                    },
                    "1.1.2": {
                        "chapter": "1.1.2",
                        "title": "生产工艺流程",
                        "description": "生产工艺流程介绍",
                        "keywords": [
                            "列举流程"
                        ],
                    },
                    "1.1.3": {
                        "chapter": "1.1.3",
                        "title": "主要生产设备",
                        "description": "主要生产设备介绍",
                        "keywords": [
                            "列举设备并对照政策文件"
                        ],
                    },
                },
            },
            "1.2": {
                "chapter": "1.2",
                "title": "企业绿色生产管理现状",
                "description": "企业依法成立、信用情况和管理职责",
                "keywords": ["依法成立", "信用", "管理", "职责"],
                "children": {
                    "1.2.1": {
                        "chapter": "1.2.1",
                        "title": "企业依法成立情况",
                        "description": "企业依法成立情况介绍",
                        "keywords": [
                            "核查材料：营业执照、房地产权证、建设工程规划许可证、环评报告、立项批复",
                            "核查方式：查材料、现场考察",
                            "企业结论：手续完善、依法设立",
                            "项目名称，节能评估",
                            "环评审批：单位，文件，时间",
                            "竣工验收：单位，文件，时间"
                        ],
                    },
                    "1.2.2": {
                        "chapter": "1.2.2",
                        "title": "企业信用情况",
                        "description": "企业信用情况介绍",
                        "keywords": [
                            "企业自成立以来，严格按照国家相关标准合法进行生产活动，建设项目严格按照法律法规执行，对各种污染源、职业健康安全隐患等进行综合治理，未发生重大生产安全、环保、质量事故。通过查询信用中国、国家企业信用信息公示系统等官方网站，企业自成立以来未发生较大生产安全、环保、质量事故，无违规违章事件。"
                        ],
                    },
                    "1.2.3": {
                        "chapter": "1.2.3",
                        "title": "企业领导绿色生产基础管理职责情况",
                        "description": "企业领导绿色生产基础管理职责介绍",
                        "keywords": [
                            "调研方式，评价对象，表现情况"
                        ],
                    },
                    "1.2.4": {
                        "chapter": "1.2.4",
                        "title": "企业绿色生产基础管理职责情况",
                        "description": "企业绿色生产基础管理职责介绍",
                        "keywords": [
                            "调研方式，评价对象，正面表述，不符合要求，核心问题"
                        ],
                    },
                },
            },
        },
    },
    "3": {
        "chapter": "3",
        "title": "绿色生产水平分析评价",
        "description": "企业绿色生产水平的全面分析评价",
        "keywords": ["绿色生产", "评价", "分析"],
        "children": {
            "3.1": {
                "chapter": "3.1",
                "title": "基础设施现状与评价",
                "description": "生产工艺设备、建筑照明等基础设施",
                "keywords": ["基础设施", "设备", "建筑", "照明", "节能"],
                "children": {
                    "3.1.1": {
                        "chapter": "3.1.1",
                        "title": "主要生产工艺设备",
                        "description": "主要生产工艺设备介绍",
                        "keywords": [
                            "企业主要从事[生产工艺]等，主要生产工艺设备含[主要设备清单]等主要生产设备，符合《产业结构调整指导目录（2024年本）》（国家发展改革委令第7号）产业准入要求，同时对照《高耗能落后机电设备（产品）淘汰目录》（第一~四批），未发现国家明令淘汰的落后设备。"
                        ],
                    },
                    "3.1.2": {
                        "chapter": "3.1.2",
                        "title": "建筑、照明及其他设备",
                        "description": "建筑节能、照明系统、通用设备等",
                        "keywords": ["建筑节能 照明系统 通用设备"],
                        "children": {
                            "3.1.2.1": {
                                "chapter": "3.1.2.1",
                                "title": "建筑节能",
                                "description": "建筑设计节材节能等情况",
                                "keywords": [
                                    "建筑设计考虑因素：节材、节能、节水、节地、无害化",
                                    "建筑结构：厂房钢结构、办公楼钢筋混凝土框架、多层",
                                    "建筑材料：高性能、低耗、本地采购、环保装修",
                                    "采光：屋顶采光带、侧窗，自然光利用",
                                    "绿化：乡土植物、适宜绿化",
                                    "再生水利用：冷却水循环系统",
                                    "评价依据：JB/T 14407-2023、GB/T 36132-2018"
                                ],
                            },
                            "3.1.2.2": {
                                "chapter": "3.1.2.2",
                                "title": "照明系统",
                                "description": "照明灯具和照明分级设计",
                                "keywords": [
                                    "照明灯具，采光，照明分级设计"
                                ],
                            },
                            "3.1.2.3": {
                                "chapter": "3.1.2.3",
                                "title": "通用设备",
                                "description": "通用设备介绍",
                                "keywords": [
                                    "通用设备数据：核查依据",
                                    "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                    "型号、容量、损耗、对标 GB 20052-2024"
                                ],
                                "children": {
                                    "3.1.2.3.1": {
                                        "chapter": "3.1.2.3.1",
                                        "title": "空气压缩机",
                                        "description": "空气压缩机介绍",
                                        "keywords": [
                                            "空气压缩机，核查依据",
                                            "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                            "型号、容量、损耗、对标 GB 20052-2024"
                                        ],
                                    },
                                    "3.1.2.3.2": {
                                        "chapter": "3.1.2.3.2",
                                        "title": "变压器",
                                        "description": "变压器介绍",
                                        "keywords": [
                                            "变压器，核查依据",
                                            "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                            "型号、容量、损耗、对标 GB 20052-2024"
                                        ],
                                    },
                                    "3.1.2.3.3": {
                                        "chapter": "3.1.2.3.3",
                                        "title": "水泵",
                                        "description": "水泵介绍",
                                        "keywords": [
                                            "水泵泵器，核查依据",
                                            "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                            "型号、容量、损耗、对标 GB 20052-2024"
                                        ],
                                    },
                                    "3.1.2.3.4": {
                                        "chapter": "3.1.2.3.4",
                                        "title": "电机",
                                        "description": "电机介绍",
                                        "keywords": [
                                            "电机，核查依据",
                                            "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                            "型号、容量、损耗、对标 GB 20052-2024"
                                        ],
                                    },
                                    "3.1.2.3.5": {
                                        "chapter": "3.1.2.3.5",
                                        "title": "冷却水循环系统",
                                        "description": "冷却水循环系统介绍",
                                        "keywords": [
                                            "冷却水循环系统，核查依据",
                                            "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                            "型号、容量、损耗、对标 GB 20052-2024"
                                        ],
                                    },
                                    "3.1.2.3.6": {
                                        "chapter": "3.1.2.3.6",
                                        "title": "空调",
                                        "description": "空调介绍",
                                        "keywords": [
                                            "空调数据，核查依据",
                                            "型号、数量、功率、能效等级 对标 GB 19153-2019",
                                            "型号、容量、损耗、对标 GB 20052-2024"
                                        ],
                                    },
                                },
                            },
                            "3.1.2.4": {
                                "chapter": "3.1.2.4",
                                "title": "计量器具配置情况",
                                "description": "计量器具配置情况",
                                "keywords": [
                                    "计量依据：GB 17167-2006"
                                ],
                            },
                            "3.1.2.5": {
                                "chapter": "3.1.2.5",
                                "title": "污染物处理设备",
                                "description": "污染物处理设备介绍",
                                "keywords": [
                                    "废气、废水、环保设备运行稳定、排放达标"
                                ],
                            },
                        },
                    },
                },
            },
            "3.2": {
                "chapter": "3.2",
                "title": "企业管理体系现状与评价",
                "description": "质量、职业健康安全、环境、能源管理体系",
                "keywords": ["管理体系", "质量", "安全", "环境", "能源"],
                "children": {
                    "3.2.1": {
                        "chapter": "3.2.1",
                        "title": "质量管理",
                        "description": "质量管理体系和第三方认证",
                        "keywords": ["质量管理", "体系", "认证"],
                        "children": {
                            "3.2.1.1": {
                                "chapter": "3.2.1.1",
                                "title": "质量管理体系",
                                "description": "质量管理体系介绍",
                                "keywords": [],
                            },
                            "3.2.1.2": {
                                "chapter": "3.2.1.2",
                                "title": "第三方认证",
                                "description": "质量管理体系第三方认证",
                                "keywords": [],
                            },
                        },
                    },
                    "3.2.2": {
                        "chapter": "3.2.2",
                        "title": "职业健康安全管理",
                        "description": "职业健康安全管理体系和第三方认证",
                        "keywords": ["职业健康", "安全管理", "体系"],
                        "children": {
                            "3.2.2.1": {
                                "chapter": "3.2.2.1",
                                "title": "职业健康安全管理体系",
                                "description": "职业健康安全管理体系介绍",
                                "keywords": [],
                            },
                            "3.2.2.2": {
                                "chapter": "3.2.2.2",
                                "title": "第三方认证",
                                "description": "职业健康安全管理体系第三方认证",
                                "keywords": [],
                            },
                        },
                    },
                    "3.2.3": {
                        "chapter": "3.2.3",
                        "title": "环境管理",
                        "description": "环境管理体系和第三方认证",
                        "keywords": ["环境管理", "体系", "认证"],
                        "children": {
                            "3.2.3.1": {
                                "chapter": "3.2.3.1",
                                "title": "环境管理体系",
                                "description": "环境管理体系介绍",
                                "keywords": [],
                            },
                            "3.2.3.2": {
                                "chapter": "3.2.3.2",
                                "title": "第三方认证",
                                "description": "环境管理体系第三方认证",
                                "keywords": [],
                            },
                        },
                    },
                    "3.2.4": {
                        "chapter": "3.2.4",
                        "title": "能源管理",
                        "description": "能源管理体系和第三方认证",
                        "keywords": ["能源管理", "体系", "认证"],
                        "children": {
                            "3.2.4.1": {
                                "chapter": "3.2.4.1",
                                "title": "能源管理体系",
                                "description": "能源管理体系介绍",
                                "keywords": [],
                            },
                            "3.2.4.2": {
                                "chapter": "3.2.4.2",
                                "title": "第三方认证",
                                "description": "能源管理体系第三方认证",
                                "keywords": [],
                            },
                        },
                    },
                    "3.2.5": {
                        "chapter": "3.2.5",
                        "title": "社会责任",
                        "description": "企业社会责任介绍",
                        "keywords": [
                            "未编制社会责任报告 保障员工权益、职业健康体检"
                        ],
                    },
                },
            },
            "3.3": {
                "chapter": "3.3",
                "title": "能源资源投入现状与评价",
                "description": "能源投入、资源投入和采购管理",
                "keywords": ["能源", "资源", "采购", "节能"],
                "children": {
                    "3.3.1": {
                        "chapter": "3.3.1",
                        "title": "能源投入",
                        "description": "能源投入介绍",
                        "keywords": ["能源消耗情况简介"],
                        "children": {
                            "3.3.1.1": {
                                "chapter": "3.3.1.1",
                                "title": "能源消耗情况",
                                "description": "能源消耗情况介绍",
                                "keywords": [
                                    "电力消耗量、折标煤量（当量值、等价值）",
                                    "天然气消耗量、折标煤量（当量值、等价值）",
                                    "煤炭消耗量、折标煤量（当量值、等价值）",
                                    "其他能源消耗量、折标煤量（当量值、等价值）",
                                    "年度综合能源消费量、折标煤量（当量值、等价值）"
                                ],
                            },
                            "3.3.1.2": {
                                "chapter": "3.3.1.2",
                                "title": "可再生能源使用情况",
                                "description": "可再生能源使用情况介绍",
                                "keywords": [
                                    "太阳能照明、光伏电站、智能微电网"
                                ],
                            },
                            "3.3.1.3": {
                                "chapter": "3.3.1.3",
                                "title": "能源管理信息化系统建设情况",
                                "description": "能源管理信息化系统建设情况介绍",
                                "keywords": [
                                    "信息化生产数据控制中心、能源信息化管理系统"
                                ],
                            },
                        },
                    },
                    "3.3.2": {
                        "chapter": "3.3.2",
                        "title": "资源投入",
                        "description": "节水、原辅材料供应情况",
                        "keywords": ["资源", "节水", "材料"],
                        "children": {
                            "3.3.2.1": {
                                "chapter": "3.3.2.1",
                                "title": "节水工作现状",
                                "description": "节水工作现状介绍",
                                "keywords": [
                                    "企业用水来源",
                                    "企业排水系统",
                                    "用水管理部门",
                                    "用水计量器具",
                                    "企业用水分类（生产、生活用水）和用途",
                                    "企业节水措施",
                                    "总用水量",
                                    "新鲜水用量",
                                    "生产用水用量",
                                    "生活用水用量",
                                    "重复用水量",
                                    "重复利用率",
                                    "生产废水排放量",
                                    "生产废水回用量",
                                    "生产废水回用率",
                                    "单位产品取水量",
                                    "行业清洁生产评价指标体系",
                                    "行业绿色工厂评价要求"
                                ],
                            },
                            "3.3.2.2": {
                                "chapter": "3.3.2.2",
                                "title": "原辅材料供应现状",
                                "description": "原辅材料供应现状介绍",
                                "keywords": [
                                    "生产主要原材料使用量、来源",
                                    "生产辅料使用量、来源",
                                    "原辅材料主要成分、理化性质",
                                    "是否属于可再生材料、绿色物料"
                                ],
                            },
                        },
                    },
                    "3.3.3": {
                        "chapter": "3.3.3",
                        "title": "采购管理现状",
                        "description": "采购管理现状介绍",
                        "keywords": [
                            "采购管理现状"
                        ],
                    },
                },
            },
            "3.4": {
                "chapter": "3.4",
                "title": "机械产品绿色评价",
                "description": "产品生态设计、有害物质、能效、碳足迹等",
                "keywords": ["产品", "绿色", "生态设计", "碳足迹"],
                "children": {
                    "3.4.1": {
                        "chapter": "3.4.1",
                        "title": "绿色（生态）设计",
                        "description": "产品生态设计介绍",
                        "keywords": [
                            "生产全过程哪些采用生态设计理念",
                            "生产过程采用先进设备提高效率",
                            "产品利于节能降碳环保",
                            "是否符合行业绿色工厂评价要求"
                        ],
                    },
                    "3.4.2": {
                        "chapter": "3.4.2",
                        "title": "有害物质使用",
                        "description": "有害物质使用介绍",
                        "keywords": [
                            "采购管理制度",
                            "原辅材料验收",
                            "管理体系",
                            "相关证书名称、编号"
                        ],
                    },
                    "3.4.3": {
                        "chapter": "3.4.3",
                        "title": "产品能效",
                        "description": "产品能效介绍",
                        "keywords": [
                            "单位产品能耗等级（若有对应行业标准）"
                        ],
                    },
                    "3.4.4": {
                        "chapter": "3.4.4",
                        "title": "产品碳足迹",
                        "description": "产品碳足迹介绍",
                        "keywords": [
                            "符合该行业的碳足迹核算和核查"
                        ],
                    },
                    "3.4.5": {
                        "chapter": "3.4.5",
                        "title": "产品环境排放",
                        "description": "产品环境排放介绍",
                        "keywords": [
                            "单位产品碳排放强度"
                        ],
                    },
                    "3.4.6": {
                        "chapter": "3.4.6",
                        "title": "回收利用率",
                        "description": "回收利用率介绍",
                        "keywords": [
                            "产品原料构成、各产品回收利用率、是否符合行业绿色工厂评价要求"
                        ],
                    },
                },
            },
            "3.5": {
                "chapter": "3.5",
                "title": "环境排放现状与评价",
                "description": "大气、水体、固体废物、噪声、温室气体排放",
                "keywords": ["排放", "废气", "废水", "固废", "噪声", "温室气体"],
                "children": {
                    "3.5.1": {
                        "chapter": "3.5.1",
                        "title": "大气污染物",
                        "description": "大气污染物介绍",
                        "keywords": [
                            "企业排放主要污染物、废气主要构成及来源"
                        ],
                        "children": {
                            "3.5.1.1": {
                                "chapter": "3.5.1.1",
                                "title": "来源和种类",
                                "description": "废气来源和种类",
                                "keywords": [
                                    "废气的构成与来源"
                                ],
                            },
                            "3.5.1.2": {
                                "chapter": "3.5.1.2",
                                "title": "处理工艺和设施",
                                "description": "废气处理工艺和设施",
                                "keywords": [
                                    "有组织排放废气的处理装置和工艺简介、企业废气治理设施统计、无组织废气构成和对应排放工序"
                                ],
                            },
                            "3.5.1.3": {
                                "chapter": "3.5.1.3",
                                "title": "排放情况",
                                "description": "废气排放情况",
                                "keywords": [
                                    "读取并总结附件内容：上一年度环境监测报告废气监测部分、各废气污染物排放总量一览"
                                ],
                            },
                        },
                    },
                    "3.5.2": {
                        "chapter": "3.5.2",
                        "title": "水体污染物",
                        "description": "水体污染物介绍",
                        "keywords": [
                            "废水主要构成及来源"
                        ],
                        "children": {
                            "3.5.2.1": {
                                "chapter": "3.5.2.1",
                                "title": "来源和种类",
                                "description": "废水来源和种类",
                                "keywords": [
                                    "来源和种类简介",
                                    "生产废水的构成和来源",
                                    "生活污水的构成和来源"
                                ],
                            },
                            "3.5.2.2": {
                                "chapter": "3.5.2.2",
                                "title": "处理工艺和设施",
                                "description": "废水处理工艺和设施",
                                "keywords": [
                                    "各类污水处理方式及设备设施（参考附件环境评价相关内容）"
                                ],
                            },
                            "3.5.2.3": {
                                "chapter": "3.5.2.3",
                                "title": "排放情况",
                                "description": "废水排放情况",
                                "keywords": [
                                    "读取并总结附件内容：上一年度环境监测报告废水监测部分、各废水和相关污染物排放总量一览"
                                ],
                            },
                        },
                    },
                    "3.5.3": {
                        "chapter": "3.5.3",
                        "title": "固废废弃物",
                        "description": "固体废物介绍",
                        "keywords": [
                            "固体废物主要构成和来源"
                        ],
                        "children": {
                            "3.5.3.1": {
                                "chapter": "3.5.3.1",
                                "title": "来源和种类",
                                "description": "固废来源和种类",
                                "keywords": [
                                    "危险废物的来源和种类、一般固废的来源和种类"
                                ],
                            },
                            "3.5.3.2": {
                                "chapter": "3.5.3.2",
                                "title": "处理方式",
                                "description": "固废处理方式",
                                "keywords": [
                                    "危险废物的处置方式、一般固废的处置方式"
                                ],
                            },
                            "3.5.3.3": {
                                "chapter": "3.5.3.3",
                                "title": "综合利用情况",
                                "description": "固废综合利用情况",
                                "keywords": [
                                    "企业固体废物处理管理制度、签订的相关固废处理协议、每年处置一般固废和危险废物的质量和占比"
                                ],
                            },
                        },
                    },
                    "3.5.4": {
                        "chapter": "3.5.4",
                        "title": "噪声",
                        "description": "噪声介绍",
                        "keywords": [
                            "噪声来源、噪声级区间、读取并总结附件内容：上一年度环境监测报告噪声监测部分"
                        ],
                    },
                    "3.5.5": {
                        "chapter": "3.5.5",
                        "title": "温室气体",
                        "description": "温室气体介绍",
                        "keywords": [
                            "查询是否属于全国碳排放权交易市场和重庆试点碳排放权交易市场重点排放单位，是否附件有第三方核查机构核查报告，且是否采用相关标准规范对其厂界范围内的温室气体排放进行核算和报告",
                            "天然气消耗量及对应碳排放因子、电力消耗量及对应碳排放因子、消耗天然气碳排放量、消耗电力碳排放量、总碳排放量"
                        ],
                    },
                },
            },
            "3.6": {
                "chapter": "3.6",
                "title": "企业绿色生产水平绩效现状与评价",
                "description": "用地集约化、原材料无害化、生产洁净化、废物资源化、能源低碳化",
                "keywords": ["绿色生产", "绩效", "评价"],
                "children": {
                    "3.6.1": {
                        "chapter": "3.6.1",
                        "title": "用地集约化",
                        "description": "用地集约化介绍",
                        "keywords": [
                            "企业用地面积、总计容建/构筑物建筑面积（计容建筑面积）、总建/构筑占地面积、产值（上一年）"
                        ],
                        "children": {
                            "3.6.1.1": {
                                "chapter": "3.6.1.1",
                                "title": "容积率",
                                "description": "容积率介绍",
                                "keywords": [
                                    "计算容积率",
                                    "比较《工业项目建设用地控制指标》（2023版）相关行业容积率的要求"
                                ],
                            },
                            "3.6.1.2": {
                                "chapter": "3.6.1.2",
                                "title": "建筑密度",
                                "description": "建筑密度介绍",
                                "keywords": [
                                    "计算建筑密度",
                                    "比较《工业项目建设用地控制指标》（2023版）相关行业建筑密度的要求"
                                ],
                            },
                            "3.6.1.3": {
                                "chapter": "3.6.1.3",
                                "title": "单位面积产出强度",
                                "description": "单位面积产出强度介绍",
                                "keywords": [
                                    "计算单位用地面积产值",
                                    "比较重庆市上一年底制造业亩均产值"
                                ],
                            },
                        },
                    },
                    "3.6.2": {
                        "chapter": "3.6.2",
                        "title": "原材料无害化",
                        "description": "原材料无害化介绍",
                        "keywords": [
                            "同类物料总使用量",
                            "绿色物料总使用量",
                            "计算绿色物料使用率",
                            "比较《绿色工厂评价指标表》中主要物料的绿色物料使用率30%及以上的要求"
                        ],
                    },
                    "3.6.3": {
                        "chapter": "3.6.3",
                        "title": "生产洁净化",
                        "description": "生产洁净化介绍",
                        "keywords": [],
                        "children": {
                            "3.6.3.1": {
                                "chapter": "3.6.3.1",
                                "title": "主要污染物排放量",
                                "description": "主要污染物排放量介绍",
                                "keywords": [
                                    "统计上文相关废水、废气、固体废物的排放量"
                                ],
                            },
                            "3.6.3.2": {
                                "chapter": "3.6.3.2",
                                "title": "废气排放量",
                                "description": "废气排放量介绍",
                                "keywords": [
                                    "计算单位产品废气排放量并与相关行业标准进行对比"
                                ],
                            },
                            "3.6.3.3": {
                                "chapter": "3.6.3.3",
                                "title": "废水排放量",
                                "description": "废水排放量介绍",
                                "keywords": [
                                    "计算单位产品废水排放量并与相关行业标准进行对比"
                                ],
                            },
                        },
                    },
                    "3.6.4": {
                        "chapter": "3.6.4",
                        "title": "废物资源化",
                        "description": "废物资源化介绍",
                        "keywords": [],
                        "children": {
                            "3.6.4.1": {
                                "chapter": "3.6.4.1",
                                "title": "单位产品主要原材料消耗量",
                                "description": "单位产品主要原材料消耗量介绍",
                                "keywords": [
                                    "统计各个工段原材料消耗量，计算单位产品原材料消耗量、成品率",
                                    "与相关行业清洁生产评价指标体系进行对比"
                                ],
                            },
                            "3.6.4.2": {
                                "chapter": "3.6.4.2",
                                "title": "工业固废综合利用率",
                                "description": "工业固废综合利用率介绍",
                                "keywords": [
                                    "计算工业固废综合利用率、对比相关标准要求"
                                ],
                            },
                            "3.6.4.3": {
                                "chapter": "3.6.4.3",
                                "title": "废水处理回用率",
                                "description": "废水处理回用率介绍",
                                "keywords": [
                                    "计算废水处理回用率、对比相关标准要求"
                                ],
                            },
                        },
                    },
                    "3.6.5": {
                        "chapter": "3.6.5",
                        "title": "能源低碳化",
                        "description": "能源低碳化介绍",
                        "keywords": [],
                        "children": {
                            "3.6.5.1": {
                                "chapter": "3.6.5.1",
                                "title": "单位产品综合能耗",
                                "description": "单位产品综合能耗介绍",
                                "keywords": [
                                    "计算各个产品综合能源消费量和单位产品综合能耗、根据不同产品对比相关清洁生产指标体系和能源消耗限额标准"
                                ],
                            },
                            "3.6.5.2": {
                                "chapter": "3.6.5.2",
                                "title": "单位产品碳排放量",
                                "description": "单位产品碳排放量介绍",
                                "keywords": [
                                    "计算各个产品消耗能源所产生的二氧化碳排放量和单位产品碳排放量",
                                    "对比产品相关清洁生产评价指标体系要求"
                                ],
                            },
                        },
                    },
                    "3.6.6": {
                        "chapter": "3.6.6",
                        "title": '"零碳"工厂建设',
                        "description": "零碳工厂建设介绍",
                        "keywords": [
                            "获取并整理附件中有关企业技术简介有关节能降碳技术、余热回收、能源管理等有关内容"
                        ],
                    },
                    "3.6.7": {
                        "chapter": "3.6.7",
                        "title": "企业绿色生产水平评价",
                        "description": "企业绿色生产水平评价介绍",
                        "keywords": [
                            "按照相关行业、产品有关绿色工厂评级要求进行评分，并对企业进行绿色工厂梯度培育分级"
                        ],
                    },
                },
            },
        },
    },
}


def get_all_chapters() -> list[tuple[str, ChapterNode]]:
    """获取所有章节列表 (chapter, node)"""
    chapters = []
    
    def _collect(node: ChapterNode, path: str = ""):
        chapter = node.get("chapter", "")
        if chapter:
            chapters.append((chapter, node))
        children = node.get("children", {})
        for key, child in children.items():
            new_path = f"{path}.{key}" if path else key
            _collect(child, new_path)
    
    for key, node in GREEN_REPORT_CHAPTERS.items():
        _collect(node, key)
    
    return chapters


def get_chapter_by_chapter(chapter: str) -> ChapterNode | None:
    """根据章节目录获取章节信息"""
    
    def _find(node: ChapterNode) -> ChapterNode | None:
        if node.get("chapter") == chapter:
            return node
        children = node.get("children", {})
        for child in children.values():
            result = _find(child)
            if result:
                return result
        return None
    
    for node in GREEN_REPORT_CHAPTERS.values():
        result = _find(node)
        if result:
            return result
    return None


def get_chapter_title(chapter: str) -> str | None:
    """根据章节目录获取章节标题"""
    node = get_chapter_by_chapter(chapter)
    return node.get("title") if node else None


def get_chapter_description(chapter: str) -> str | None:
    """根据章节目录获取章节描述"""
    node = get_chapter_by_chapter(chapter)
    return node.get("description") if node else None


def get_chapter_keywords(chapter: str) -> list[str]:
    """根据章节目录获取关键词列表"""
    node = get_chapter_by_chapter(chapter)
    return node.get("keywords", []) if node else []


def get_all_chapter_codes() -> list[str]:
    """获取所有章节目录列表"""
    result = []
    for chapter, _ in get_all_chapters():
        result.append(chapter)
    return result


def get_chapter_tree() -> dict[str, ChapterNode]:
    """获取完整的章节树"""
    return GREEN_REPORT_CHAPTERS


def flatten_chapters() -> dict[str, ChapterNode]:
    """扁平化章节树，返回 {chapter: node} 格式"""
    result = {}
    
    def _flatten(node: ChapterNode, path: str):
        chapter = node.get("chapter", "")
        if chapter:
            result[chapter] = node
        children = node.get("children", {})
        for key, child in children.items():
            new_path = f"{path}.{key}" if path else key
            _flatten(child, new_path)
    
    for key, node in GREEN_REPORT_CHAPTERS.items():
        _flatten(node, key)
    
    return result
