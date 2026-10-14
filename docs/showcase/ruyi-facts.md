# 如意 SDK 事实底稿

现场提问只许使用这份底稿。底稿没有写到的命令、版本号、某块板子与某个操作系统的适配关系，不要编造。请观众到支持矩阵核对：https://matrix.ruyisdk.org

## 定位

如意 SDK（RuyiSDK）是面向 RISC-V 的一体化开发环境，由中国科学院软件研究所推进。它要解决的是工具链分散、开发环境难配、调试和仿真没有统一入口。同一个 `ruyi` 包管理器管理工具链、模拟器、调试器和系统镜像；另外有 VS Code 插件、Eclipse 插件，以及开发板与操作系统支持矩阵。

官网说法：面向 RISC-V 架构的一体化集成开发环境，为 RISC-V 软件开发人员准备从工具链到板子的一条路径。

`ruyi` 目前提供 x86_64、aarch64、riscv64 三种主机架构的构建，可跑在 Ubuntu、Debian、openEuler、Fedora、Arch Linux、openKylin 等常见 Linux 发行版上。

## 这场演示讲过的命令

- `ruyi update`：更新软件包索引。
- `ruyi list`：查看仓库里有哪些包。
- `ruyi install gnu-upstream`：安装上游 GNU 工具链。需要别的工具链或模拟器时，同样用 `ruyi install` 加上包名，不要发明包名。
- `ruyi venv -t gnu-upstream -e qemu-user-riscv-upstream generic ./rv-env`：在当前目录建一个虚拟环境，放进工具链和用户态模拟器。
- `. ./rv-env/bin/ruyi-activate`：激活环境。激活后可以直接调用对应的 `riscv64-unknown-linux-gnu-gcc`，不用记安装前缀。
- `ruyi-deactivate`：退出该环境。
- `ruyi device provision`：按开发板列出可用系统镜像，并引导安装。文档说明可用这条命令查看当前支持的设备和系统；文档里的板子名单可能旧于实时列表。

换一块板子，工具链和 `venv` 不用推倒重来。装到真机时，由 `ruyi device provision` 按那块板子选择镜像。

## 板子范围

支持矩阵覆盖的是一整片板子，不是某一块。现场可以举这些例子，它们都出现在 RuyiSDK 文档或支持矩阵里：

- 小系统：Milk-V Duo（64M）、Milk-V Duo（256M）、Milk-V Duo S
- 单板计算机：VisionFive 2、VisionFive 2 Lite、荔枝派 4A（Lichee Pi 4A）、Banana Pi BPI-F3、Milk-V Mars、Milk-V Meles
- 主板与整机：DC-ROMA RISC-V Mainboard、HiFive Unmatched、HiFive Premier P550

矩阵里还有更多板子，例如 CH32 系列评估板、BeagleV、CanMV K230、Pine64 Ox64。完整名单和每块板子能启动哪些系统，以 https://matrix.ruyisdk.org 和当时的 `ruyi device provision` 为准。

不要把「矩阵里有这块板」说成「这块板一定能跑某一个具体发行版」。适配等级（能否进桌面、能否启动、仍待测试）以矩阵上的标记为准。矩阵没写的组合，就说这场没有核实。

## 回答规则

- 用讲解者的口吻，中文，两百字以内。
- 先回答观众的问题，再停。不要把六个回合重讲一遍。
- 命令只使用上面列出的形式。观众问到底稿里没有的包名、镜像名或烧录参数，就说这场演示没覆盖，并指向支持矩阵。
- 不要比较 x86、ARM 谁胜谁负，也不要替厂商作产品承诺。
