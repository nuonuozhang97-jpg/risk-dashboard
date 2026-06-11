# 全球风险日报 - 风险监控面板

每天自动更新的全球风险监控面板，覆盖自然灾害、疫情、市场行情、行业新闻、竞品动态。

## 功能

🌍 **自然灾害** - 地震(M4.5+)、台风、洪水、火山（USGS + GDACS）
🦠 **疫情监测** - 全球疫情通报（ProMED）
📊 **市场行情** - 汇率、国债收益率、大宗商品
📰 **行业新闻 & 政策** - 半导体行业新闻、中国工信部政策
🏭 **竞品动态** - 全球主要半导体公司新闻

## 技术栈

- **前端**: 纯HTML + CSS + JavaScript（无依赖）
- **数据源**: USGS、GDACS、ProMED、Frankfurter、RSS feeds
- **自动化**: GitHub Actions（每天北京时间8点自动更新）
- **托管**: GitHub Pages

## 部署指南

### 如果你有GitHub账号：

1. 在GitHub上创建一个新仓库（例如 `risk-dashboard`）
2. 把 `scripts/` 和 `site/` 目录推上去，同时把 `.github/` 也推上去
3. 在仓库 Settings → Pages 中：
   - Source 选 **Deploy from a branch**
   - Branch 选 `gh-pages`，目录选 `/ (root)`
4. 手动触发一次 Actions 看看能不能跑通
5. 之后每天早上8点自动更新

### 如果没有GitHub账号：

先注册一个 → https://github.com/signup （免费，5分钟）
然后按上面的步骤操作。如果不会操作Git，告诉我，我手把手教你。
