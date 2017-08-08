#!/bin/bash

#
# gen_makefile.sh 是分析 BUILD 文件、生成 Makefile 的工具
#
# 给定一个 BUILD 文件的路径， 
# 解析该 BUILD 文件，
# 分析 library 之间的依赖关系，
# 自动生成 Makefile，
# 免去手工生成和维护 Makefile 的痛苦.
#
# BUILD 文件简介：
#
#   简单的讲，BUILD 文件是 Makefile 文件的替代品; 
#   通过 gen_makefile.sh 解析 BUILD 文件，可以生成完善的 Makefile。
#
#   BUILD 文件记录了同一个目录下 (称为一个 package，包), 多个 C++ 源文件如何组织，包括：
#     - 哪些 C++ 源文件编译成 静态链接库
#     - 哪些 C++ 源文件编译成 二进制可执行程序
#     - 库和库之间，以及 可执行程序和库之间 的 链接依赖关系
#     - 和其他包下的库之间的链接依赖关系
#
#   BUILD 文件中可以定义 4 种目标
#     cc_library()  生成一个 静态链接库
#     cc_binary()   生成一个 二进制可执行程序
#     cc_test()     生成一个 单元测试可执行程序
#     cc_data()     指定库、程序 或者 单元测试 运行时必要的数据文件
#
#   BUILD 文件实际上是一个 python 程序，可以调用上述几个函数，用来声明构建目标。
#   这四个函数主要参数有两个：name 和 srcs，分别用于指定 名称 和 源文件列表
#  
#   例子 1：
#     cc_library(name = "greet", 
#                srcs = ["greet.cc",
#                        "hello.cc",
#                        ],
#                )
#     声明一个静态链接库，库名为 "greet"，源代码是 greet.cc 和 hello.cc
#       name: 是一个字符串，标识该构建目标的名字
#       srcs: 是字符串列表，每个字符串是一个源代码文件路径
#             文件路径只能是相对路径，且必须在 BUILD 所在目录或者其子目录下
#
#   例子 2：
#     cc_library(name = "greet",
#                srcs = ["greet.cc",
#                        "hello.cc",
#                        ],
#                deps = ["//net/http/BUILD:downloader"],
#                )
#     同 例子 1，且该库依赖另外一个包下的库，
#     被依赖的包位于源码根目录下的 net/http 目录，库名是 downloader
#
#   例子 3：
#     cc_binary(name = "hello_world",
#               srcs = ["main.cc"],
#               deps = ["//base/common/BUILD:base",
#                       ":greet",
#                       ],
#               )
#
#     声明一个二进制可执行程序，依赖外部库 base/common/BUILD:base，且依赖包内库 greet。
#     写依赖项列表 deps 时，
#       "//" 代表 codebase 根目录，
#       ":" 之前是被依赖的包的 BUILD 文件路径，
#       ":" 之后是被依赖的库的名字
#       若 ":" 之前的部分省略，则表示依赖的包就是当前 BUILD 文件
#
#   例子 4：
#     cc_test(name = "hell_world_test",
#             srcs = ["hello_world_test.cc"],
#             deps = ["//base/testing/BUILD:test_main",
#                     ":greet",
#                     ],
#             )
#
#     声明一个单元测试可执行程序
#
#   完整的例子可以参见 samples/tutorial/BUILD
#
#   此外：
#     - BUILD 文件语法非常简洁，不用记忆 Makefile 的各种复杂规则
#     - 相比于手工编写的 Makefile，解析 BUILD 自动生成的 Makefile 更完善、更强大
#     - 解析 BUILD 文件的工具，针对我们的应用需求作优化，生成的 Makefile 有如下优点:
#        - 完善的 unit test 支持
#        - 默认链接性能测试库，可以很方便的查找程序的 性能瓶颈、内存瓶颈、内存泄漏 和 内存错误
#        - 自动分析 C++ 源文件和头文件的依赖关系
#        - 自动检查依赖关系的变更，必要时通知用户重新生成 Makefile
#        - 自动发布静态链接库和头文件
#        - 自动打包程序及其依赖的库、数据，供线上使用 (自动打包数据功能未实现)
#
#   要求：
#     为了支持上述自动化 单元测试、发布、打包，有如下要求:
#     1. 可执行程序、单元测试程序的工作目录 (又称启动目录 或 working dir),
#        必须是 代码库根目录(有文件 BLADE_ROOT 标识该目录);
#     2. 库、可执行程序和单元测试程序 在加载内部数据的时候 (比如分词库加载的分词词典)
#        使用的文件路径必须是相对于代码库根目录的 相对路径;
#     3. 在 代码库根目录 下开发和运行测试，使得不同库在加载词典文件的时候，
#        都可以用代码库根目录作为相对目录的起始目录
#
#
# NOTE 1:
#
#   自动生成的 Makefile，支持下列 make 指令，详情如下：
#
#   基本指令:
#       make                等同于 make dbg
#
#       make dbg            编译所有 lib, binary, test 的 debug (调试) 版, 
#                           生成的 .a 库文件和 可执行文件 位于 .build/dbg/targets 目录下
#
#       make opt            编译所有 lib, binary, test 的 optimized (优化) 版, 
#                           生成的 .a 库文件和 可执行文件 位于 .build/opt/targets 目录下
#
#       make diag_dbg       编译所有 lib, binary, test 的 debug diagnosis (调试诊断) 版, 
#                           生成的 .a 库文件和 可执行文件 位于 .build/diag_dbg/targets 目录下
#                           diag_dbg 打开了运行时内存错误检查, 可用于线下诊断 dbg 版代码中的内存错误
#
#       make diag_opt       编译所有 lib, binary, test 的 optimized diagnosis (优化诊断) 版, 
#                           生成的 .a 库文件和 可执行文件 位于 .build/diag_opt/targets 目录下
#                           diag_opt 打开了运行时内存错误检查, 可用于线下诊断 opt 版代码中的内存错误
#
#       make all            生成 dbg, opt, diag_dbg, diag_opt 4 个版本的目标
#
#       make clean          清除编译生成的中间文件
#
#       make dbg_test       编译并运行所有 debug (调试) 版的单元测试
#       make opt_test       编译并运行所有 optimized (调试) 版的单元测试
#       make diag_dbg_test  编译并运行所有 debug diagnosis (调试诊断) 版的单元测试
#       make diag_opt_test  编译并运行所有 optimized diagnosis (调试诊断) 版的单元测试
#
#       make all_test       编译并运行上述全部单元测试
#       make test           等同于 make dbg_test
#
#       make lint           检查所有源文件是否符合 code style, 代码风格文档见 code_style 目录
#                           同时也检查一些经典的错误代码
#
#       make static_check   检查所有源文件是否包含常见的 C++ 编程错误
#
#   高级指令:
#       make test_until_failed      编译并反复运行所有调试版和优化版单元测试，直到测试失败；
#                                   打印失败之前单元测试正常运行的轮数。
#       make dbg_test_until_failed  编译并反复运行所有调试版的单元测试，直到测试失败；
#                                   打印失败之前单元测试正常运行的轮数。 
#       make opt_test_until_failed  编译并反复运行所有调试版的单元测试，直到测试失败；
#                                   打印失败之前单元测试正常运行的轮数。
#
#   发布指令:
#       make pub  运行所有单元测试，若单元测试通过，则按如下规则发布 packages 
#                 (假设 BUILD 文件所在目录为 $PACKAGE_DIR):
#                 - 拷贝包内所有 头文件 (*.h), 单元测试文件 (*_test.cc) 到 pub/src/$PACKAGE_DIR
#                 - 拷贝调试版静态链接库 .build/dbg/targets/$PACKAGE_DIR/*.a 到 pub/dbg/targets/$PACKAGE_DIR
#                 - 拷贝优化版静态链接库 .build/opt/targets/$PACKAGE_DIR/*.a 到 pub/opt/targets/$PACKAGE_DIR
#                 - 拷贝包内所有 data 文件 (由 cc_data 指令声明) 到 pub/src/$PACKAGE_DIR
#                 - 如果希望将源码只读发布，可以用 cc_data 指令, 将源码当作数据，发布之
#
#
# NOTE 2:
#
#   生成的 Makefile 里，会把如下 2 个目录加入到 C++ 的 include path 中：
#     - ./
#       代码库的根目录，包含大家开发/发布的代码
#     - build_tools/third_party/include
#       包含所有必要的第三方库，除特殊情况外，不允许直接使用该目录下的头文件
#
#
# NOTE 3:
#
#   如果 BUILD 文件里，依赖的库只在 pub/src 目录下存在，
#   则会在源码根目录建立符号链接。
#   例如：如果 BUILD 文件里有 deps = ["//extend/regexp/BUILD:pcre"],
#         需要依赖 extend/regexp/BUILD 包下的 pcre 库
#         但包对应的头文件在 pub/src/extend/regexp 目录下，
#         则该脚本正常执行后，会建立符号链接 extend/regexp，指向 pub/src/extend/regexp。
#         这样, C++ 源文件就可以这样来包含头文件 
#             #include "extend/pcre/pcre.h"
#         而不需要这样
#             #include "pub/src/extend/pcre/pcre.h"
#
#
# NOTE 4:
#
#   在多核 CPU 机器上，可以加上参数 "-j n" 来多核加速，n 是希望利用的 CPU 核的数目
#   例如，可以运行命令 "$ make -j4 dbg opt"，
#   用 4 个 CPU 核同时开工，编译程序的 debug 版和 optimized 版
# 
#
# NOTE 5:
#
#   运行 make 指令时，默认会在屏幕输出详细的编译命令行；
#   可以加上 "-s" 参数，使得只输出较精简的信息
# 
#
# NOTE 6:
#
#   如果需要生成的 Makefile 支持多个不同的 package
#   可以一次解析多个 BUILD 文件, 命令行如下：
#   $ bash gen_makefile.sh xxx/BUILD yyy/BUILD zzz/BUILD
# 
#
# NOTE 7:
#
#   如果 gcc 编译报错，错误消息包含繁杂的 C++ 模板信息，
#   可以在 make 的时候，加上参数 SIMPLIFY_GCC=yes,
#   简化 gcc 的输出，帮助理解编译错误
#
#
# NOTE 8:
#
#   如果需要解析 xxx 目录下的所有 BUILD 文件, 可以用如下命令行：
#   $ find xxx -name BUILD | xargs bash gen_makefile.sh
#
# NOTE 9:
#
#   BUILD 文件还可以定义下列目标
#     proto_library()    生成 protobuffer 静态库
#     cc_mpi_library()   生成支持 mpi 的静态库
#     cc_mpi_binary()    生成支持 mpi 的可执行程序
#     cc_jni_library()   生成 jni 静态库
#     cc_pyext()         生成 python 扩展库
#     shell_script()     生成 shell 脚本
#     ss_test()          生成 shell 脚本，可由 make ss_test 自动执行
#

set -u

if [ ! -f "BLADE_ROOT" ] ; then
  echo "$0 must run under the root dir of the codebase"
  exit -1
fi

if [ $# -eq 0 ]; then
  echo "Please specify a BUILD file"
  echo "Usage: bash $0 [ PATH_TO_BUILD_FILE |...]"
  exit
fi

for b in $*; do
  if echo "$b" | grep "/BUILD$" > /dev/null; then
    true
  else
    echo "not a BUILD file: '$b'"
    echo "please specify a path to a BUILD file"
    exit -1
  fi
done

# 建立所有库的头文件的目录链接
bash ./list_pub_libs.sh > /dev/null

[ $? -ne 0 ] && echo "Failed to run ./list_pub_libs.sh" && exit 1

rm -f Makefile
mkdir -p .build/pb/c++

if [ $# -eq 1 ] && [ $1 = "ALL" ]; then
  # 为所有 BUILD 文件，生成 Makefile (刨除 ./pub 和 ./sandbox 目录下的 BUILD 文件)
  all_build=`find . -name BUILD | grep -v "\./pub/" | grep -v "\./sandbox/"`

  python2.6 build_tools/blade3/pconfig.pyc $all_build && \
  echo "" && \
  echo "The Makefile is generated succesfully." && \
  echo "" && \
  echo "BUILD files below are parsed:" && \
  echo $all_build

else
  # 生成新的 Makefile
  python2.6 build_tools/blade3/pconfig.pyc $* && \
  echo "" && \
  echo "The Makefile is generated succesfully."

fi

