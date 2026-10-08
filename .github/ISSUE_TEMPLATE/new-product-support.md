name: 新产品支持请求
description: 你用的国产 AI Agent 产品不在 askill 支持列表里？提这里，目标一周内支持
title: "[新产品] "
labels: ["new-product"]
body:
  - type: markdown
    attributes:
      value: |
        感谢提供一线信息——这类 issue 是 askill 覆盖面扩张最主要的输入。
        填得越全，适配越快；不确定的字段留空即可，我们会跟进。

  - type: input
    id: product-name
    attributes:
      label: 产品名称与公司
      description: 例如「Trae CN（字节跳动）」
    validations:
      required: true

  - type: textarea
    id: skills-path
    attributes:
      label: skills 目录路径（知道几个填几个）
      description: macOS / Windows / Linux 下的技能目录。不确定可以在产品安装目录找 skills、user_skills 等关键词，或贴官方文档链接。
      placeholder: |
        Windows: %USERPROFILE%\.newprod\skills\
        macOS: ~/.newprod/skills/
    validations:
      required: false

  - type: dropdown
    id: install-form
    attributes:
      label: 产品形态
      options:
        - CLI / 终端工具
        - 桌面 App
        - IDE 插件
        - 仅网页/移动端（无本地目录）
    validations:
      required: true

  - type: textarea
    id: frontmatter
    attributes:
      label: SKILL.md 有没有特殊要求？
      description: 例如要求额外的 frontmatter 字段（如 description_zh）、特殊命名、版本号格式等。不清楚就填「不知道」。
    validations:
      required: false

  - type: textarea
    id: extra
    attributes:
      label: 其他信息
      description: settings.json 开关、技能商店机制、官方文档链接、以及任何踩坑记录。
    validations:
      required: false

  - type: checkboxes
    attributes:
      label: 意向确认
      options:
        - label: 我愿意在新版本发布后帮忙实测验证（最好注明可用平台）
