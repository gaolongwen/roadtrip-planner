#!/usr/bin/env python3
"""更新数据库：使用飞书表格中的真实参考链接"""

import sqlite3

# 从飞书API结果中提取的景点名称和参考链接
# 格式: (景点名, 参考链接)
references = [
    ("云冈石窟", "https://www.xiaohongshu.com/explore/68f4b820000000000400566f"),
    ("晋华宫国家矿山公园", "https://www.xiaohongshu.com/explore/68bc3257000000001d01fcbb"),
    ("八台教堂", "https://www.xiaohongshu.com/explore/68ac6ebe000000001d036b0e"),
    ("永安禅寺", "https://www.xiaohongshu.com/explore/68dd02b40000000003034d55"),
    ("华严寺", "https://www.xiaohongshu.com/explore/6903007c0000000007036be6"),
    ("善化寺", "https://www.xiaohongshu.com/explore/681b582f0000000022037386"),
    ("土林", "https://www.xiaohongshu.com/explore/68cbd516000000001203c75f"),
    ("大同火山群", "https://www.xiaohongshu.com/explore/675a592c000000000603a06f"),
    ("应县木塔", "https://www.xiaohongshu.com/explore/68e873a3000000000700a04f"),
    ("广武明长城", "https://www.xiaohongshu.com/explore/68dd6677000000000301c3e6"),
    ("崇福寺", "https://www.xiaohongshu.com/explore/68cd5e8900000000130053e7"),
    ("南禅寺", "https://www.xiaohongshu.com/explore/6890addd000000002302fb76"),
    ("延庆寺", "https://www.xiaohongshu.com/explore/68fda814000000000301079f"),
    ("广济寺", "https://www.xiaohongshu.com/explore/68b3338d000000001c0330f3"),
    ("猫村", "https://www.xiaohongshu.com/explore/681d9fdb0000000023001cf0"),
    ("洪福寺", "https://www.xiaohongshu.com/explore/68f5877100000000040131f7"),
    ("悬空村", "https://www.xiaohongshu.com/explore/68f606c40000000005031fe7"),
    ("万年冰窟", "https://www.xiaohongshu.com/explore/689ee56a000000001c030c94"),
    ("后马仑村", "https://www.xiaohongshu.com/explore/68f78c170000000007031841"),
    ("秀容书院", "https://www.xiaohongshu.com/explore/68d55db0000000001302ba97"),
    ("雁门关", "https://www.xiaohongshu.com/explore/68d28b90000000000e0335d6"),
    ("大汖古村", "https://www.xiaohongshu.com/explore/68ce65a200000000120326a3"),
    ("青石寺", "https://www.xiaohongshu.com/discovery/item/68b6dfec000000001b03346b"),
    ("藏山景区", "https://www.xiaohongshu.com/discovery/item/6757f373000000000102a2ae"),
    ("晋祠", "https://www.xiaohongshu.com/discovery/item/68e1df4a0000000003023811"),
    ("百年天主教堂", "https://www.xiaohongshu.com/discovery/item/68c236d8000000001c00fcaf"),
    ("铁猫寺", "https://www.xiaohongshu.com/discovery/item/68ce51260000000012015945"),
    ("竖石佛摩崖石刻造像", "https://www.xiaohongshu.com/discovery/item/68d697bb0000000013010dd7"),
    ("东龙观墓群", "https://www.xiaohongshu.com/explore/68fda800000000000503388b"),
    ("双林寺", "https://www.xiaohongshu.com/explore/686811a5000000000b01e591"),
    ("GoHome艺术中心", "https://www.xiaohongshu.com/discovery/item/661aa17c000000001a01046c"),
    ("金灯寺", "https://www.xiaohongshu.com/explore/68baa027000000001d00dc7f"),
    ("龙门寺", "https://www.xiaohongshu.com/explore/687b9d5f000000000d01bce9"),
    ("原起寺", "https://www.xiaohongshu.com/explore/68d2c8fd000000000702a072"),
    ("霓虹村", "https://www.xiaohongshu.com/explore/688b6fbc0000000025025911"),
    ("岳家寨", "https://www.xiaohongshu.com/explore/673db24c00000000020299bc"),
    ("法兴寺", "https://www.xiaohongshu.com/explore/68e4dad20000000003011af7"),
    ("小西天", "https://www.xiaohongshu.com/explore/6896fc86000000002302d33c"),
    ("广胜寺", "https://www.xiaohongshu.com/explore/69086e3f0000000003018aba"),
    ("水神庙", "https://www.xiaohongshu.com/explore/6827182b0000000023017b9c"),
    ("南杜壁村教堂", "https://www.xiaohongshu.com/explore/68dc876700000000040173df"),
    ("临汾千佛崖", "https://www.xiaohongshu.com/explore/68dbf27a00000000040128b1"),
    ("壶口瀑布", "https://www.xiaohongshu.com/explore/689302ec0000000022020c74"),
    ("汾城古建筑群", "https://www.xiaohongshu.com/discovery/item/68fc9f7000000000070225a8"),
    ("青莲寺", "https://www.xiaohongshu.com/explore/68eb91690000000005039ddc"),
    ("大箕古堡", "https://www.xiaohongshu.com/explore/678e12dc000000001701d436"),
    ("6200年银杏王", "https://www.xiaohongshu.com/explore/672abb1f000000001d03982c"),
    ("羊头山石刻", "https://www.xiaohongshu.com/explore/6774a230000000000b00f4e9"),
    ("仙翁庙", "https://www.xiaohongshu.com/explore/67d2d6f700000000090165f0"),
    ("海会寺", "https://www.xiaohongshu.com/explore/63f24d5600000000130134b1"),
    ("龙兴寺", "https://www.xiaohongshu.com/explore/68a09dee000000001c035511"),
    ("绛州文庙", "https://www.xiaohongshu.com/explore/686a51bf0000000015022382"),
    ("绛州三楼（钟鼓乐）", "https://www.xiaohongshu.com/explore/674ff9480000000002019ace"),
    ("稷山稷王庙", "https://www.xiaohongshu.com/explore/660d7e95000000001a00ed8a"),
    ("大佛寺", "https://www.xiaohongshu.com/explore/689dfa79000000001d0169a3"),
    ("马村砖雕墓", "https://www.xiaohongshu.com/explore/69044edc0000000004003406"),
    ("飞云楼", "https://www.xiaohongshu.com/explore/68ee2ff70000000007039d6d"),
    ("万荣稷王庙", "https://www.xiaohongshu.com/explore/68b4376b000000001d008c0c"),
    ("万荣李家大院", "https://www.xiaohongshu.com/explore/685ffc5900000000120143fa"),
    ("后土祠", "https://www.xiaohongshu.com/explore/681422ff000000000b01639e"),
    ("孤峰山", "https://www.xiaohongshu.com/explore/6905a5d80000000005012915"),
    ("鹳雀楼", "https://www.xiaohongshu.com/explore/68c43685000000001d026d47"),
    ("普救寺", "https://www.xiaohongshu.com/explore/684cfc5e0000000012005dcb"),
    ("万固寺", "https://www.xiaohongshu.com/explore/68e0b1e300000000030389a7"),
]

conn = sqlite3.connect('/root/.openclaw/workspace/roadtrip-planner/backend/data/roadtrip.db')
cursor = conn.cursor()

# 清空错误的图片数据（之前手动添加的百度图片）
cursor.execute("UPDATE pois SET images = '[]', reference_url = NULL")
print("已清空旧数据")

# 更新参考链接
updated = 0
for name, url in references:
    cursor.execute(
        "UPDATE pois SET reference_url = ? WHERE name = ?",
        (url, name)
    )
    if cursor.rowcount > 0:
        updated += 1

conn.commit()
conn.close()

print(f"✅ 更新了 {updated} 个景点的参考链接")
print()
print("说明：")
print("- 图片字段暂时清空（飞书表格中大部分为空）")
print("- 参考链接改为小红书笔记（真实数据）")
