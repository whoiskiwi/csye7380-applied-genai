# 在 Explorer 集群上跑实验

本地 Mac 跑本地模型太慢、会卡，所以把实验放到学校 Explorer 集群的 GPU 上跑。代码不用改：作业脚本会在 GPU 节点上启动 Ollama（Research Computing 推荐用 Apptainer 容器），再跑实验。

课程 GPU 分区 `courses-gpu` 的限制：每个作业最长 8 小时，同时只能有 1 个作业，内存 12 GB。

作业脚本指定要 V100（32 GB 显存，`--gres=gpu:v100-sxm2:1`）。这个分区还有 12 GB 显存的 P100，放不下 14b 和 3b 两个模型，Ollama 会在每次调用时来回卸载、加载模型，慢到可能超过 8 小时。V100 只有两台机器（d1004、d1011），被占用时作业会排队等待；`sinfo -p courses-gpu -o '%N %G %t'` 可以看哪台空闲。

## 第 0 步：登录

终端里执行（`<用户名>` 是你的 Northeastern 用户名）：

```bash
ssh <用户名>@login.explorer.northeastern.edu
groups                      # 确认课程组已经在列表里；没有的话退出重新登录
ls /courses                 # 找到本课程的文件夹名，例如 CSYE7380.xxxxx
```

## 第 1 步：把项目传上去（在你的 Mac 上执行）

macOS 自带的 rsync（openrsync）和集群不兼容，所以用 tar 打包后经 ssh 传过去：

```bash
cd ~/Desktop/csye7380-applied-genai
COPYFILE_DISABLE=1 tar --no-xattrs -czf - --exclude .venv --exclude runs --exclude '__pycache__' didu-squad \
  | ssh <用户名>@login.explorer.northeastern.edu "tar xzf - -C /courses/<课程文件夹>/students/<用户名>/"
```

如果 `/courses/...` 路径不存在，就先传到家目录：把 `-C` 后面的路径换成 `~/`。

`data/cache/llm/` 里是本地已经跑过的模型回答，一起传上去；集群上用同一个模型时可以直接复用。

## 第 2 步：一次性安装（在集群登录节点执行）

```bash
cd /courses/<课程文件夹>/students/<用户名>/didu-squad    # 或 ~/didu-squad
bash hpc/setup.sh
```

它会安装 uv、建立 Python 环境、下载 Ollama 容器和两个模型（都放在 `/scratch/<用户名>/ers/`），最后跑一遍测试。

Ollama 固定用 0.6.8 版：更新的版本要求 NVIDIA 驱动 550 以上，而 `courses-gpu` 节点的驱动是 545，新版会悄悄退回 CPU 运行（一次回答要 5 分钟以上）。作业开始时会检查 Ollama 是否用上了 GPU，并让每个模型先答一句话计时，不正常就直接报错退出。

模型必须在登录节点下载：GPU 计算节点不能上网，作业里只读取已经下载好的模型，缺模型时会直接报错退出。

## 第 3 步：提交实验

```bash
sbatch hpc/run_mvp.sbatch                     # 主实验：3 个场景 × 3 个种子 × 4 种方法
squeue -u $USER                               # 看作业状态（PD 排队，R 运行中）
tail -f hpc/logs/ers-mvp-<作业号>.out          # 看进度
```

想先试一下流程是否通，可以先跑几秒钟就结束的 mock 版：`sbatch hpc/run_mvp.sbatch configs/exp_smoke.yaml`。

模型默认分两档：贵档 qwen2.5:14b（医院协调、总指挥），便宜档 qwen2.5:3b（其余 agent），都是免费开源模型。想换模型可以这样提交：`ERS_MODEL_STRONG=qwen2.5:7b sbatch --export=ALL hpc/run_mvp.sbatch`。

## 第 4 步：把结果拿回本地（在你的 Mac 上执行）

```bash
cd ~/Desktop/csye7380-applied-genai/didu-squad
ssh <用户名>@login.explorer.northeastern.edu \
  "cd /courses/<课程文件夹>/students/<用户名>/didu-squad && tar czf - runs data/cache/llm" | tar xzf -
PYTHONPATH=src uv run --no-sync streamlit run app/streamlit_app.py     # 本地回放
```

结果报告在 `runs/mvp_results.md`。

## 注意

- `/scratch` 每 28 天清空，只放模型和容器；结果在项目文件夹里，不会被清。
- 集群维护公告在 Research Computing 的 Status Updates 页面，作业异常时先看那里。
- 作业日志里有 `nvidia-smi` 的输出，可以看到分到的是哪种 GPU。
