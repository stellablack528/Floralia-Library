/* ============================================================
   Florentia · 花与书页 — 花卉资料卡（Oxford Flower17 全部 17 类）
   说明：
   - 学名采用各分类群通行的中文资料名称，正式核对以
     Kew POWO / 《中国植物志》为准（项目阶段零）。
   - 花语与寓意为西方花语文化的通用整理，属项目赏析；
     具体文学引文待核对原文与出处后补充。
   - order 字段与 Flower17 类别编号一致，供识别演示使用。
   ============================================================ */
window.FF = window.FF || {};

FF.data = {
  flowers: [
    {
      key: "daffodil", order: 1, zh: "黄水仙", en: "Daffodil",
      latin: "Narcissus pseudonarcissus", family: "石蒜科 · 水仙属",
      speak: "新生 · 希望 · 重生",
      meaning: "黄水仙是欧洲春天最早开放的花之一，常被视为寒冬结束、新生活开始的信号。华兹华斯笔下摇曳的水仙，使它成为英语文学里「孤独心灵被治愈」的经典意象。传说中那喀索斯化为水仙的故事，则提醒凝视与自省的两面。",
      traits: ["花被片6枚，副冠呈喇叭状", "花茎中空，一茎一花", "叶基生，扁平带状"],
      season: "原产西欧伊比利亚半岛至阿尔卑斯一带，多在早春 3—4 月开花（因气候而异）",
      note: "资料卡为界面演示；学名与花期描述待按 Kew POWO 与《中国植物志》逐条核对。"
    },
    {
      key: "lily", order: 2, zh: "白百合", en: "Lily",
      latin: "Lilium candidum", family: "百合科 · 百合属",
      speak: "纯洁 · 庄严 · 无瑕",
      meaning: "白百合在欧洲绘画传统中常与圣洁形象相伴，是「纯洁」最古老的花语载体。它的六枚舒展花被与浓烈甜香，让它同时带有庄严与热烈的双重气质。",
      traits: ["花被片6枚，常反卷", "茎单生，散生叶", "花瓣白色，具黄色基部"],
      season: "原产地中海东部地区，初夏开花（具体物候随产地而异）",
      note: "Flower17 中 Lily 类别包含多种百合；对应物种待核对。"
    },
    {
      key: "bluebell", order: 3, zh: "蓝铃花", en: "Bluebell",
      latin: "Hyacinthoides non-scripta", family: "天门冬科 · 蓝铃花属",
      speak: "谦逊 · 感恩 · 永恒的爱",
      meaning: "蓝铃花在英国古老林地里成片铺开，被称为「仙女之铃」。低垂的钟形小花仿佛不愿争抢目光，于是「谦逊」与「含蓄的守候」成了它最常被引用的寓意。",
      traits: ["钟形蓝紫色小花，下垂成串", "叶片狭长基生", "茎常弯曲，穗状花序"],
      season: "常见于西欧落叶林地，春末开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "fritillary", order: 4, zh: "花格贝母", en: "Fritillary",
      latin: "Fritillaria meleagris", family: "百合科 · 贝母属",
      speak: "壮丽之中带哀愁",
      meaning: "花格贝母的花瓣织着棋盘格纹，在欧洲花语里被赋予「辉煌与哀愁并存」的复杂意味。它一度在野生草甸中濒临消失，也让「珍惜易逝之美」成为后人附加的注脚。",
      traits: ["花被片具明显棋盘格斑", "单生花，下垂", "茎细直，叶稀疏线形"],
      season: "原产欧洲中部与西部草甸，春末开花（具体物候随产地而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "iris", order: 5, zh: "鸢尾", en: "Iris",
      latin: "Iris germanica", family: "鸢尾科 · 鸢尾属",
      speak: "信念 · 智慧 · 希望",
      meaning: "属名 Iris 来自希腊神话中的彩虹女神，她是天与地之间的信使。鸢尾因此在花语里承担「传递信念」的角色，法国王室纹章上的 fleur-de-lis 也常与它相联系。",
      traits: ["花被片6枚，外轮下垂、内轮直立", "叶剑形，排成扇状", "花色多为蓝紫"],
      season: "原产欧洲南部，晚春至初夏开花（因品种与气候而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "tiger-lily", order: 6, zh: "卷丹", en: "Tiger Lily",
      latin: "Lilium lancifolium", family: "百合科 · 百合属",
      speak: "自信 · 热烈 · 骄傲",
      meaning: "橙红色花瓣上洒满深色斑点，如虎纹般张扬，卷丹的花语因此带着毫不掩饰的自信与生命力。它在东亚园林中自古有栽培记录，是东西方都熟悉的「火焰色百合」。",
      traits: ["花瓣强烈反卷，橙红具紫黑斑点", "叶腋生紫黑色珠芽", "花下垂，数朵成总状"],
      season: "原产东亚，盛夏开花（具体物候随产地而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "dandelion", order: 7, zh: "蒲公英", en: "Dandelion",
      latin: "Taraxacum officinale", family: "菊科 · 蒲公英属",
      speak: "自由 · 许愿 · 无法停留的爱",
      meaning: "吹散蒲公英的时刻几乎属于每一种童年。绒球随风而散的姿态，让它同时承载「许愿」与「离别」两种寓意——愿望被送走，种子落向新的土地。",
      traits: ["头状花序全为舌状黄花", "叶基生，羽状深裂", "果实具冠毛，聚成绒球"],
      season: "广布欧亚温带，春至秋季均可开花（因气候而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "cowslip", order: 8, zh: "黄花九轮草", en: "Cowslip",
      latin: "Primula veris", family: "报春花科 · 报春花属",
      speak: "青春的来临 · 初恋",
      meaning: "黄花九轮草是英国草甸早春的金色信号，一束小花从莲座叶丛中央探出。它的花语与「青春初启」相连；在莎士比亚时代的民间传统里，它还被认为有开启心扉的力量。",
      traits: ["伞形花序，数朵金黄色小花", "花冠筒长，喉部有橙纹", "叶皱，基生莲座状"],
      season: "原产欧洲，春季开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "buttercup", order: 9, zh: "毛茛", en: "Buttercup",
      latin: "Ranunculus acris", family: "毛茛科 · 毛茛属",
      speak: "童真 · 谦逊的魅力",
      meaning: "「你举起毛茛花照向我的下巴，说爱金色的人就该戴金色。」——这句英格兰童谣式的测试，让毛茛成了「孩子气的喜欢」的代名词。光泽如漆的花瓣在阳光下几乎发光。",
      traits: ["花5枚黄色花瓣，光泽明显", "茎直立，多分枝", "叶掌状深裂"],
      season: "原产欧洲与西亚，晚春至初夏开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "windflower", order: 10, zh: "林地银莲花", en: "Windflower",
      latin: "Anemone nemorosa", family: "毛茛科 · 银莲花属",
      speak: "期待 · 随风而至的讯息",
      meaning: "属名 Anemone 源自希腊语的「风」，风吹过 woodland，白色小花便随之摇曳。它的花语写的是「等待风带来的消息」——期待与轻愁各占一半。",
      traits: ["花被片6—8枚，白色常带粉晕", "无花瓣，实为萼片状花被", "叶掌状三深裂"],
      season: "原产欧洲落叶林地，早春开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "pansy", order: 11, zh: "三色堇", en: "Pansy",
      latin: "Viola tricolor", family: "堇菜科 · 堇菜属",
      speak: "思念 · 心上之人",
      meaning: "法语的 pensée（思念）给了 Pansy 名字。花如其名：三色花瓣像一张写着心事的脸。维多利亚花语中，把它送给一个人等于说「你在想她/他」。",
      traits: ["花大，常三色（紫、黄、白）", "花瓣具深色侧瓣斑", "叶互生，卵圆形，具圆钝锯齿"],
      season: "原产欧洲，耐寒，冷凉季节开花（栽培品种花期因园艺管理而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "crocus", order: 12, zh: "春番红花", en: "Crocus",
      latin: "Crocus vernus", family: "鸢尾科 · 番红花属",
      speak: "青春的喜悦 · 破土的希望",
      meaning: "雪尚未化尽，番红花已从土里顶出紫色杯状花。它是最早的春信之一，花语「破土的希望」由此而来；它是藏红花（Crocus sativus）的近亲，却开得更早、更任性。",
      traits: ["杯状花，紫色或条纹", "花被片6枚", "叶狭线形，中央具银白条带"],
      season: "原产欧洲高山草甸，早春（或秋花种在秋季）开花（因种而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "snowdrop", order: 13, zh: "雪滴花", en: "Snowdrop",
      latin: "Galanthus nivalis", family: "石蒜科 · 雪滴花属",
      speak: "希望 · 安慰 · 新的开始",
      meaning: "雪滴花在雪地里垂下乳白色小铃铛，是北温带最早开花的球根植物之一。欧洲传统里，把它带进室内象征「冬天终将过去」，因而有了「希望与安慰」的花语。",
      traits: ["花下垂，钟形，白色", "内轮花被片带绿色斑", "叶狭长，基生两枚"],
      season: "原产欧洲，冬末早春开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "colchicum", order: 14, zh: "秋水仙", en: "Colchicum",
      latin: "Colchicum autumnale", family: "秋水仙科 · 秋水仙属",
      speak: "我的最美时光 · 秋日迟来的告白",
      meaning: "秋水仙在别的花凋谢的九月突然破土开花，无叶无茎，像大地迟来的告白。它美丽却有毒——这份「不可轻易触碰」，也让花语里掺进了距离感。",
      traits: ["花被片6枚，淡粉紫色", "秋季无叶开花", "叶春季长出，宽披针形"],
      season: "原产欧洲中部，秋季开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "tulip", order: 15, zh: "郁金香", en: "Tulip",
      latin: "Tulipa gesneriana", family: "百合科 · 郁金香属",
      speak: "博爱 · 完美的宣言",
      meaning: "郁金香曾掀起十七世纪荷兰的疯狂，杯形花冠被视为「盛满阳光的酒杯」。红色郁金香在花语里是直接的爱的宣言，而杂色的珍稀球根则成了财富与欲望的注脚。",
      traits: ["杯状花，花被片6枚离生", "叶宽披针形，灰绿", "花色丰富，单花顶生"],
      season: "原产中亚至土耳其一带，春季开花（因气候而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "wallflower", order: 16, zh: "桂竹香", en: "Wallflower",
      latin: "Erysimum cheiri", family: "十字花科 · 糖芥属",
      speak: "恒久 · 忠实于困境中的爱",
      meaning: "桂竹香偏爱旧墙与石缝，在最贫瘠的角落开出橙黄与深红的花。它因此被赋予「在困境中依然忠诚」的花语；英文里 wallflower 也成了「安静站在墙边的人」的借喻。",
      traits: ["总状花序，花橙黄至砖红", "花被4枚，十字形排列", "叶披针形，全缘"],
      season: "原产欧洲南部，春末开花（因地区而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    },
    {
      key: "sunflower", order: 17, zh: "向日葵", en: "Sunflower",
      latin: "Helianthus annuus", family: "菊科 · 向日葵属",
      speak: "仰慕 · 忠诚 · 沉默的爱",
      meaning: "花盘追随太阳转向，向日葵把「仰慕」写成了可以看见的动作。梵高的画让它又多一层寓意：即使生命短暂，也要用尽全力明亮。",
      traits: ["头状花序大，舌状花金黄", "茎粗壮，被粗毛", "叶心形，具长柄"],
      season: "原产北美洲，夏季开花（因地区与播种期而异）",
      note: "资料卡为界面演示；学名与花期描述待逐条核对。"
    }
  ]
};

FF.data.byKey = function (key) {
  return this.flowers.find(f => f.key === key) || null;
};

/* 识别演示模式：基于文件字节特征做确定性「伪识别」，
   同一张图总得到同一结果；模型接入后替换为真实推理。 */
FF.data.demoIdentify = function (byteSum, byteMod) {
  const idx = (byteSum * 7 + byteMod * 13) % this.flowers.length;
  const primary = this.flowers[idx];
  const second = this.flowers[(idx + 5 + byteMod % 4) % this.flowers.length];
  const third = this.flowers[(idx + 11 + byteSum % 3) % this.flowers.length];
  const p1 = 62 + (byteSum % 31);           /* 62–92% */
  const rest = 100 - p1;
  const p2 = Math.max(2, Math.round(rest * ((byteMod % 5 + 3) / 10)));
  const p3 = Math.max(1, rest - p2);
  return [
    { flower: primary, score: p1 },
    { flower: second, score: p2 },
    { flower: third, score: p3 }
  ];
};
