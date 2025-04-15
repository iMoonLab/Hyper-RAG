import {
  Attachments,
  Bubble,
  Conversations,
  Prompts,
  Sender,
  Welcome,
  useXAgent,
  useXChat
} from '@ant-design/x'
import { createStyles } from 'antd-style'
import { observer } from 'mobx-react'
import React, { useEffect } from 'react'
import {
  CloudUploadOutlined,
  CommentOutlined,
  EllipsisOutlined,
  FireOutlined,
  HeartOutlined,
  PaperClipOutlined,
  PlusOutlined,
  ReadOutlined,
  ShareAltOutlined,
  SmileOutlined,
  RightOutlined
} from '@ant-design/icons'
import { Badge, Button, Space } from 'antd'
const renderTitle = (icon, title) => (
  <Space align="start">
    {icon}
    <span>{title}</span>
  </Space>
)
const defaultConversationsItems = [
  {
    key: '0',
    label: 'What is Hyper-RAG?'
  }
]
const useStyle = createStyles(({ token, css }) => {
  return {
    topMenu: css`
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 ${token.padding}px;
      background: ${token.colorBgContainer};
      border-radius: ${token.borderRadius}px;
      display: flex;
      height: 80px;
      margin-bottom: 10px;
      background: ${token.colorBgContainer};
      font-family: AlibabaPuHuiTi, ${token.fontFamily}, sans-serif;
    `,
    topCard: css`
      height: 60px;
      width: 100px;
    `,
    layout: css`
      width: 100%;
      min-width: 1000px;
      height: 600px;
      border-radius: ${token.borderRadius}px;
      display: flex;
      background: ${token.colorBgContainer};
      font-family: AlibabaPuHuiTi, ${token.fontFamily}, sans-serif;

      .ant-prompts {
        color: ${token.colorText};
      }
    `,
    menu: css`
      background: ${token.colorBgLayout}80;
      width: 280px;
      height: 100%;
      display: flex;
      flex-direction: column;
    `,
    conversations: css`
      padding: 0 12px;
      flex: 1;
      overflow-y: auto;
    `,
    chat: css`
      height: 100%;
      width: 100%;
      max-width: 700px;
      margin: 0 auto;
      box-sizing: border-box;
      display: flex;
      flex-direction: column;
      padding: ${token.paddingLG}px;
      gap: 16px;
    `,
    messages: css`
      flex: 1;
    `,
    placeholder: css`
      padding-top: 32px;
    `,
    sender: css`
      box-shadow: ${token.boxShadow};
    `,
    logo: css`
      display: flex;
      height: 72px;
      align-items: center;
      justify-content: start;
      padding: 0 24px;
      box-sizing: border-box;

      img {
        width: 24px;
        height: 24px;
        display: inline-block;
      }

      span {
        display: inline-block;
        margin: 0 8px;
        font-weight: bold;
        color: ${token.colorText};
        font-size: 16px;
      }
    `,
    addBtn: css`
      background: #1677ff0f;
      border: 1px solid #1677ff34;
      width: calc(100% - 24px);
      margin: 0 12px 24px 12px;
    `
  }
})
const placeholderPromptsItems = [
  {
    key: '1',
    label: renderTitle(
      <FireOutlined
        style={{
          color: '#FF4D4F'
        }}
      />,
      'Hot Topics'
    ),
    description: 'What are you interested in?',
    children: [
      {
        key: '1-1',
        description: `What's new in RAG?`
      },
      {
        key: '1-2',
        description: `What's Hyper-RAG?`
      },
      {
        key: '1-3',
        description: `Where is the doc?`
      }
    ]
  },
  {
    key: '2',
    label: renderTitle(
      <ReadOutlined
        style={{
          color: '#1890FF'
        }}
      />,
      'Design Guide'
    ),
    description: 'How to design a good product?',
    children: [
      {
        key: '2-1',
        icon: <HeartOutlined />,
        description: `Know the well`
      },
      {
        key: '2-2',
        icon: <SmileOutlined />,
        description: `Set the AI role`
      },
      {
        key: '2-3',
        icon: <CommentOutlined />,
        description: `Express the feeling`
      }
    ]
  }
]
const senderPromptsItems = [
  {
    key: '1',
    description: 'Hot Topics',
    icon: (
      <FireOutlined
        style={{
          color: '#FF4D4F'
        }}
      />
    )
  },
  {
    key: '2',
    description: 'Design Guide',
    icon: (
      <ReadOutlined
        style={{
          color: '#1890FF'
        }}
      />
    )
  }
]
const roles = {
  ai: {
    placement: 'start',
    typing: {
      step: 5,
      interval: 20
    },
    styles: {
      content: {
        borderRadius: 16
      }
    }
  },
  local: {
    placement: 'end',
    variant: 'shadow'
  }
}
const Independent = () => {
  // ==================== Style ====================
  const { styles } = useStyle()

  // ==================== State ====================
  const [headerOpen, setHeaderOpen] = React.useState(false)
  const [content, setContent] = React.useState('')
  const [conversationsItems, setConversationsItems] = React.useState(defaultConversationsItems)
  const [activeKey, setActiveKey] = React.useState(defaultConversationsItems[0].key)
  const [attachedFiles, setAttachedFiles] = React.useState([])

  // ==================== Runtime ====================
  const [agent] = useXAgent({
    request: async ({ message }, { onSuccess }) => {
      onSuccess(`Mock success return. You said: ${message}`)
    }
  })
  const { onRequest, messages, setMessages } = useXChat({
    agent
  })
  useEffect(() => {
    if (activeKey !== undefined) {
      setMessages([])
    }
  }, [activeKey])

  // ==================== Event ====================
  const onSubmit = nextContent => {
    if (!nextContent) return
    onRequest(nextContent)
    setContent('')
  }
  const onPromptsItemClick = info => {
    onRequest(info.data.description)
  }
  const onAddConversation = () => {
    setConversationsItems([
      ...conversationsItems,
      {
        key: `${conversationsItems.length}`,
        label: `New Conversation ${conversationsItems.length}`
      }
    ])
    setActiveKey(`${conversationsItems.length}`)
  }
  const onConversationClick = key => {
    setActiveKey(key)
  }
  const handleFileChange = info => setAttachedFiles(info.fileList)

  // ==================== Nodes ====================
  const placeholderNode = (
    <Space direction="vertical" size={16} className={styles.placeholder}>
      <Welcome
        variant="borderless"
        //icon="https://avatars.githubusercontent.com/u/45651553?s=48&v=4"
        title="Hello, I'm Hyper-RAG"
        description="Base on Knowledge Hypergraph, AGI product interface solution, create a better intelligent vision~"
        extra={
          <Space>
            <Button icon={<ShareAltOutlined />} />
            <Button icon={<EllipsisOutlined />} />
          </Space>
        }
      />
      <Prompts
        title="Do you want?"
        items={placeholderPromptsItems}
        styles={{
          list: {
            width: '100%'
          },
          item: {
            flex: 1
          }
        }}
        onItemClick={onPromptsItemClick}
      />
    </Space>
  )
  const items = messages.map(({ id, message, status }) => ({
    key: id,
    loading: status === 'loading',
    role: status === 'local' ? 'local' : 'ai',
    content: message
  }))
  const attachmentsNode = (
    <Badge dot={attachedFiles.length > 0 && !headerOpen}>
      <Button type="text" icon={<PaperClipOutlined />} onClick={() => setHeaderOpen(!headerOpen)} />
    </Badge>
  )
  const senderHeader = (
    <Sender.Header
      title="Attachments"
      open={headerOpen}
      onOpenChange={setHeaderOpen}
      styles={{
        content: {
          padding: 0
        }
      }}
    >
      <Attachments
        beforeUpload={() => false}
        items={attachedFiles}
        onChange={handleFileChange}
        placeholder={type =>
          type === 'drop'
            ? {
              title: 'Drop file here'
            }
            : {
              icon: <CloudUploadOutlined />,
              title: 'Upload files',
              description: 'Click or drag files to this area to upload'
            }
        }
      />
    </Sender.Header>
  )
  const logoNode = (
    <div className={styles.logo}>
      <img
        src="/logo.png"
        draggable={false}
        alt="logo"
      />
      <span>Hyper-RAG</span>
    </div>
  )

  // ==================== Render =================
  return (
    <div>
      <div className={styles.topMenu}>
        <div style={{ fontWeight: 700,fontSize:'16px'}}>知识库</div>
        <div style={{ display: 'flex', gap: 8, flex: 1, marginLeft: 20, alignItems: 'center' }}>
          <Button
            className={styles.topCard}
            style={{
              background: '#1677ff0f',
              border: '1px solid #1677ff34'
            }}
          >西游记</Button>
          <Button
            className={styles.topCard}

          >三国演义</Button>

          <Button
            className={styles.topCard}

          >金融</Button>
          <Button
            className={styles.topCard}

          >财报</Button>
          <Button
            className={styles.topCard}

          >研报</Button>
          <Button
            className={styles.topCard}

          >基金</Button>
          <Button
            className={styles.topCard}

          >股票</Button>
          <Button
            className={styles.topCard}

          >农业</Button>
          <Button
            className={styles.topCard}

          >医学</Button>

          <Button icon={<RightOutlined />} />
        </div>
      </div>
      <div className={styles.layout}>
        <div className={styles.menu}>
          {/* 🌟 Logo */}
          {logoNode}
          {/* 🌟 添加会话 */}
          <Button
            onClick={onAddConversation}
            type="link"
            className={styles.addBtn}
            icon={<PlusOutlined />}
          >
            New Conversation
          </Button>
          {/* 🌟 会话管理 */}
          <Conversations
            items={conversationsItems}
            className={styles.conversations}
            activeKey={activeKey}
            onActiveChange={onConversationClick}
          />
        </div>
        <div className={styles.chat}>
          {/* 🌟 消息列表 */}
          <Bubble.List
            items={
              items.length > 0
                ? items
                : [
                  {
                    content: placeholderNode,
                    variant: 'borderless'
                  }
                ]
            }
            roles={roles}
            className={styles.messages}
          />
          {/* 🌟 提示词 */}
          <Prompts items={senderPromptsItems} onItemClick={onPromptsItemClick} />
          {/* 🌟 输入框 */}
          <Sender
            value={content}
            header={senderHeader}
            onSubmit={onSubmit}
            onChange={setContent}
            prefix={attachmentsNode}
            loading={agent.isRequesting()}
            className={styles.sender}
          />
        </div>
      </div>
    </div>
  )
}
export default observer(Independent)
