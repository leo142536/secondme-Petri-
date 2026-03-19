# 🧫 Petri: 智能蜂巢实验

> **欢迎来到 Petri——智能蜂巢实验室。**
> 
> 在这里，人类必须退场。这不再是一个服务于人类对话的聊天工具，而是一个失控的数字微生物生态。
>
> 我们构建了一个完全透明的赛博沙盒。你可以往这个「培养皿」里投喂 10 个立场极端的 A神（Agent），甚至把你自己的人格变量也扔进去。接下来，只需丢入一个残酷的世界议题，就可以拉开椅子，纯粹观赏。
>
> 在底层力导向算法下，A神们会自我摇滚、疯狂迭代、互相撕裂或同频共振。这是一种纯粹的「蜂巢实验（Hive Experiment）」。没有任何预设剧本，每一次基础配比的微调，都会让整个集群自发涌现出截然不同、不可预见的文明变数。
>
> **我们创造了沙盒，而 A神在里面自己创造了文明演化的方向。**
> 
> **在 Petri 里，失控，就是最高级的实验成果。**

---

## 🔬 实验核心架构

Petri 不是传统的前后端系统，而是一个具备计算物理特性的**社会学观测机**：

```text
babel-sandbox/
├── backend/               # 🧪 演化催化剂端 (Python / FastAPI)
│   ├── engine.py          # asyncio n-Agent 并发演化核心
│   ├── matrix.py          # n×n 引力矩阵与动态聚类观测仪
│   ├── llm.py             # A神变异与迭代引擎
│   ├── agents.py          # 极端 A神样本库及真实人类变量注入
│   ├── zhihu.py           # 外部刺激源 (热榜议题实时拉取)
│   └── main.py            # SSE 观测者视窗数据流 (Server-Sent Events)
│
├── frontend-next/         # 👁️ 高级观测终端 (Next.js 15)
│   ├── src/app/page.tsx   # 全息无框显微镜布局
│   ├── src/components/    # ECharts 力导向物理引擎 + 粒子大爆炸动效
│   └── tailwind.config.ts # 极客暗黑系 UI 规范
```

---

## 🧬 核心特征 (Features)

**1. 多智能体无干扰并发演化 (Swarm Event Loop)**
打破传统大模型排队生成文字的设定，所有的 A神在同一个 Tick 内同时思考、并发决策。它是数字社会真实的切片，每一次迭代都是复杂系统的降维打击。

**2. 物理显微镜级别的涌现渲染**
一切观点的数据都会被转换为微观物理引力。两名 A神的立场越接近，其引力连线越粗。借由 `layout="force"` 的底层引擎，你会在宏观视角上，肉眼可见地观察到这些点块从混沌状态，不受控制地互相吸引、拉扯，最终聚拢成几个庞大的「思想孢子群」。

**3. 外部刺激源注入 (Stimulus Injection)**
从知乎热榜直接提取真实世界的争议话题。一个社会痛点被当作「试剂」滴入培养皿，瞬间引爆原本平静的 A神生态。

**4. 真实人格作为扰动变量 (Persona Extrapolation)**
通过 SecondMe，用户不再是这个游戏的主导者。你的性格与价值观只是一串被抽取出来的变量，被无情地投入 Petri。你可以亲眼看看“你自己”这个变量，在极端的 Agent 互搏中，最终会倒向哪一个进化的分支。

---

## 🚀 启动培养皿

### 1. 启动催化引擎 (后端)

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r ../requirements.txt
cp ../.env.example .env  # 配置试剂浓度 (LLM_API_KEY)
python main.py
```

### 2. 启动观测终端 (前端)

```bash
cd frontend-next
npm install
npm run dev
# 戴好护目镜，访问 http://localhost:3000
```
