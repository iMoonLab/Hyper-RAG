import React, { useState } from 'react'
import { Card, Tag, Collapse, Badge, Tooltip, Typography, Space, Divider } from 'antd'
import { useTranslation } from 'react-i18next'
import {
  NodeIndexOutlined,
  ShareAltOutlined,
  FileTextOutlined,
  InfoCircleOutlined,
  DatabaseOutlined
} from '@ant-design/icons'

const { Panel } = Collapse
const { Text, Paragraph } = Typography

const RetrievalInfo = ({
  entities = [],
  hyperedges = [],
  textUnits = [],
  className = '',
  mode = 'hyper'
}) => {
  const [activeKey, setActiveKey] = useState([])
  const { t } = useTranslation()

  // 如果没有任何检索信息，不渲染组件
  if (!entities.length && !hyperedges.length && !textUnits.length) {
    return null
  }
  const edgesName = mode === 'hyper' ? t('retrieval.hyperedge_count') : t('retrieval.edge_count')

  const renderEntityCard = (entity, index) => (
    <Card
      key={index}
      size="small"
      className="mb-2"
      title={
        <Space>
          <NodeIndexOutlined className="text-blue-500" />
          <Text strong>{entity.entity_name}</Text>
          <Tag color="blue">{entity.entity_type}</Tag>
        </Space>
      }
    >
      <div className="text-sm">
        {entity.description && (
          <div className="mb-2">
            <Text type="secondary">{t('retrieval.description')}: </Text>
            <Paragraph
              ellipsis={{ rows: 2, expandable: true, symbol: t('retrieval.expand') }}
              className="mb-1"
            >
              {entity.description}
            </Paragraph>
          </div>
        )}
        {entity.additional_properties && entity.additional_properties !== 'UNKNOWN' && (
          <div className="mb-2">
            <Text type="secondary">{t('retrieval.properties')}: </Text>
            <Text>{entity.additional_properties}</Text>
          </div>
        )}
        <div className="flex justify-between items-center">
          <span>
            <Text type="secondary">{t('retrieval.relevance')}: </Text>
            <Badge count={entity.rank || 0} showZero style={{ backgroundColor: '#52c41a' }} />
          </span>
        </div>
      </div>
    </Card>
  )

  const renderHyperedgeCard = (hyperedge, index) => (
    <Card
      key={index}
      size="small"
      className="mb-2"
      title={
        <Space>
          <ShareAltOutlined className="text-green-500" />
          <Text strong>
            {edgesName} #{index + 1}
          </Text>
        </Space>
      }
    >
      <div className="text-sm">
        <div className="mb-2">
          <Text type="secondary">{t('retrieval.connected_entities')}: </Text>
          <div className="mt-1">
            {Array.isArray(hyperedge.entity_set) ? (
              hyperedge.entity_set.map((entity, idx) => (
                <Tag key={idx} color="green" className="mb-1">
                  {entity}
                </Tag>
              ))
            ) : (
              <Tag color="green">{hyperedge.entity_set}</Tag>
            )}
          </div>
        </div>

        {hyperedge.description && (
          <div className="mb-2">
            <Text type="secondary">{t('retrieval.description')}: </Text>
            <Paragraph
              ellipsis={{ rows: 2, expandable: true, symbol: t('retrieval.expand') }}
              className="mb-1"
            >
              {hyperedge.description}
            </Paragraph>
          </div>
        )}

        {hyperedge.keywords && (
          <div className="mb-2">
            <Text type="secondary">{t('retrieval.keywords')}: </Text>
            <Text italic>{hyperedge.keywords}</Text>
          </div>
        )}

        <div className="flex justify-between items-center">
          <span>
            <Text type="secondary">{t('retrieval.weight')}: </Text>
            <Tag color="orange">{hyperedge.weight || 0}</Tag>
          </span>
          <span>
            <Text type="secondary">{t('retrieval.relevance')}: </Text>
            <Badge count={hyperedge.rank || 0} showZero style={{ backgroundColor: '#52c41a' }} />
          </span>
        </div>
      </div>
    </Card>
  )

  const renderTextUnit = (textUnit, index) => (
    <Card
      key={index}
      size="small"
      className="mb-2"
      title={
        <Space>
          <FileTextOutlined className="text-purple-500" />
          <Text strong>
            {t('retrieval.document_fragment')} #{index + 1}
          </Text>
        </Space>
      }
    >
      <Paragraph
        ellipsis={{ rows: 3, expandable: true, symbol: t('retrieval.expand') }}
        className="text-sm mb-0"
      >
        {textUnit.content}
      </Paragraph>
    </Card>
  )

  const panelItems = []

  // 超边面板
  if (hyperedges.length > 0) {
    panelItems.push({
      key: 'hyperedges',
      label: (
        <Space>
          <ShareAltOutlined className="text-green-500" />
          <span>
            {mode === 'hyper'
              ? t('retrieval.retrieved_hyperedges')
              : t('retrieval.retrieved_edges')}
          </span>
          <Badge count={hyperedges.length} style={{ backgroundColor: '#52c41a' }} />
        </Space>
      ),
      children: (
        <div className="max-h-80 overflow-y-auto">{hyperedges.map(renderHyperedgeCard)}</div>
      )
    })
  }

  // 实体面板
  if (entities.length > 0) {
    panelItems.push({
      key: 'entities',
      label: (
        <Space>
          <NodeIndexOutlined className="text-blue-500" />
          <span>{t('retrieval.retrieved_entities')}</span>
          <Badge count={entities.length} style={{ backgroundColor: '#1890ff' }} />
        </Space>
      ),
      children: <div className="max-h-80 overflow-y-auto">{entities.map(renderEntityCard)}</div>
    })
  }

  // 文档片段面板
  if (textUnits.length > 0) {
    panelItems.push({
      key: 'textUnits',
      label: (
        <Space>
          <FileTextOutlined className="text-purple-500" />
          <span>{t('retrieval.retrieved_documents')}</span>
          <Badge count={textUnits.length} style={{ backgroundColor: '#722ed1' }} />
        </Space>
      ),
      children: <div className="max-h-80 overflow-y-auto">{textUnits.map(renderTextUnit)}</div>
    })
  }

  return (
    <div className={`mt-4 ${className}`}>
      <div className="mb-3 flex items-center">
        <DatabaseOutlined className="text-gray-500 mr-2" />
        <Text strong className="text-gray-700">
          {t('retrieval.retrieval_info_details')}
        </Text>
        <Tooltip title={t('retrieval.retrieval_info_tooltip')}>
          <InfoCircleOutlined className="text-gray-400 ml-1" />
        </Tooltip>
      </div>

      <Collapse
        items={panelItems}
        activeKey={activeKey}
        onChange={setActiveKey}
        size="small"
        className="bg-gray-50"
      />
    </div>
  )
}

export default RetrievalInfo
