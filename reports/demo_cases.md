# 端到端演示案例

## text：商业银行资本充足率不得低于多少？

```
Answer: 第五条 商业银行资本充足率不得低于8%
Type: text | Confidence: 0.850 | Status: answered

Evidence 1:
  第五条 商业银行资本充足率不得低于8%。

Evidence 2:
  第四条 商业银行一级资本充足率不得低于6%。

Evidence 3:
  第三条 商业银行核心一级资本充足率不得低于5%。

Evidence 4:
  第六条 商业银行杠杆率不得低于4%。

Evidence 5:
  第二章 资本充足率要求

Source 1:
  商业银行资本管理办法.docx | Article: 第五条 | Section: 第二章 资本充足率要求

Source 2:
  商业银行资本管理办法.docx | Article: 第四条 | Section: 第二章 资本充足率要求

Source 3:
  商业银行资本管理办法.docx | Article: 第三条 | Section: 第二章 资本充足率要求

Source 4:
  商业银行资本管理办法.docx | Article: 第六条 | Section: 第二章 资本充足率要求

Source 5:
  商业银行资本管理办法.docx | Section: 第二章 资本充足率要求
```

## text：银行业金融机构发生重大事项后，应当在多少日内报告？

```
Answer: 第三条 银行业金融机构发生重大事项后，应当在5个工作日内向监管机构报告
Type: text | Confidence: 0.850 | Status: answered

Evidence 1:
  第三条 银行业金融机构发生重大事项后，应当在5个工作日内向监管机构报告。

Evidence 2:
  第一条 为规范银行业金融机构重大事项报告工作，制定本制度。

Evidence 3:
  第四条 发生特别重大事项的，应当在24小时内先行电话报告，并在3个工作日内补报书面材料。

Evidence 4:
  第五条 季度报告应当于每季度结束后20日内报送。

Evidence 5:
  第七条 重大事项报告应当包括事项基本情况、影响分析、拟采取的处置措施。

Source 1:
  银行业金融机构重大事项报告制度.docx | Article: 第三条 | Section: 第二章 报告时限

Source 2:
  银行业金融机构重大事项报告制度.docx | Article: 第一条 | Section: 第一章 总则

Source 3:
  银行业金融机构重大事项报告制度.docx | Article: 第四条 | Section: 第二章 报告时限

Source 4:
  银行业金融机构重大事项报告制度.docx | Article: 第五条 | Section: 第二章 报告时限

Source 5:
  银行业金融机构重大事项报告制度.docx | Article: 第七条 | Section: 第三章 报告内容
```

## table：2024年一季度商业银行营业收入是多少亿元？

```
Answer: 135.2亿元
Type: table | Confidence: 1.000 | Status: answered

Evidence 1:
  指标：营业收入
  期间：商业银行主要监管指标统计表 / 2024年 / 一季度
  值：135.2
  单位：亿元

Source 1:
  商业银行主要监管指标统计表.xlsx | Sheet: 年度数据 | Cell: E4
```

## table：B机构2024年末营业收入比A机构高多少亿元？

```
Answer: 150亿元
Type: table | Confidence: 0.900 | Status: answered

Evidence 1:
  指标：B机构 / 营业收入
  期间：2024年末
  值：450
  单位：亿元

Evidence 2:
  指标：A机构 / 营业收入
  期间：2024年末
  值：300
  单位：亿元

Source 1:
  银行业金融机构资产负债统计表.xlsx | Sheet: 机构数据 | Cell: C7

Source 2:
  银行业金融机构资产负债统计表.xlsx | Sheet: 机构数据 | Cell: C4
```

## no_evidence：某机构发生数据泄露后应当在多少日内报告金融监管总局？

```
Answer: 未找到足够证据
Type: text | Confidence: 0.539 | Status: no_evidence

Evidence 1:
  第三条 银行业金融机构发生重大事项后，应当在5个工作日内向监管机构报告。

Evidence 2:
  第五条 季度报告应当于每季度结束后20日内报送。

Evidence 3:
  第四条 发生特别重大事项的，应当在24小时内先行电话报告，并在3个工作日内补报书面材料。

Evidence 4:
  第十二条 商业银行应当于每季度结束后30日内向监管机构报送资本充足率报表。

Evidence 5:
  第六条 年度报告应当于年度结束后3个月内报送。

Source 1:
  银行业金融机构重大事项报告制度.docx | Article: 第三条 | Section: 第二章 报告时限

Source 2:
  银行业金融机构重大事项报告制度.docx | Article: 第五条 | Section: 第二章 报告时限

Source 3:
  银行业金融机构重大事项报告制度.docx | Article: 第四条 | Section: 第二章 报告时限

Source 4:
  商业银行资本管理办法.docx | Article: 第十二条 | Section: 第四章 监督检查

Source 5:
  银行业金融机构重大事项报告制度.docx | Article: 第六条 | Section: 第二章 报告时限
```
