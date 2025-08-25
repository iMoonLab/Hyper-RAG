import React, { useMemo } from 'react'
import { Graphin } from '@antv/graphin'
import { useTranslation } from 'react-i18next'

const colors = [
  '#F6BD16',
  '#00C9C9',
  '#F08F56',
  '#D580FF',
  '#FF3D00',
  '#16f69c',
  '#004ac9',
  '#f056d1',
  '#a680ff',
  '#c8ff00'
]

//  colors 加深
const entityTypeColors = {
  PERSON: '#00C9C9',
  CONCEPT: '#a68fff',
  ORGANIZATION: '#F08F56',
  LOCATION: '#16f69c',
  EVENT: '#004ac9',
  PRODUCT: '#f056d1'
}

const RetrievalHyperGraph = ({
  entities = [],
  hyperedges = [],
  height = '300px',
  width = '100%',
  showTooltip = true,
  containerStyle = {},
  graphId = 'retrieval-hypergraph',
  mode = 'hyper' // 新增mode参数，默认为hyper模式
}) => {
  const { t } = useTranslation()
  const edgesName = mode === 'hyper' ? t('retrieval.hyperedge_count') : t('retrieval.edge_count')
  // 转换数据格式为HyperGraph组件需要的格式
  const convertedData = useMemo(() => {
    // 如果没有数据，返回空
    if (!entities.length && !hyperedges.length) {
      return null
    }

    const vertices = {}
    const edges = {}

    // 处理实体数据
    entities.forEach(entity => {
      const entityName = String(entity.entity_name || entity.name || `Entity_${Math.random()}`)
      vertices[entityName] = {
        ...entity,
        entity_type: String(entity.entity_type || t('retrieval.unknown')),
        description: String(entity.description || ''),
        label: String(entity.entity_name || entity.name || '')
      }
    })

    // 处理超边数据
    hyperedges.forEach((edge, index) => {
      // 构建超边的键名，使用|#|分隔实体
      let edgeKey
      if (Array.isArray(edge.entity_set)) {
        edgeKey = edge.entity_set.map(e => String(e)).join('|#|')
      } else if (typeof edge.entity_set === 'string') {
        edgeKey = edge.entity_set
      } else if (edge.id_set) {
        // 如果没有entity_set但有id_set，使用id_set
        edgeKey = Array.isArray(edge.id_set)
          ? edge.id_set.map(e => String(e)).join('|#|')
          : String(edge.id_set)
      } else {
        edgeKey = `edge_${index}`
      }

      // 确保超边中的实体也在vertices中
      const entityNames = edgeKey.split('|#|')
      entityNames.forEach(entityName => {
        if (!vertices[entityName]) {
          vertices[entityName] = {
            entity_type: t('retrieval.unknown'),
            description: `${t('retrieval.entity_from_hyperedge')}: ${entityName}`
          }
        }
      })

      edges[edgeKey] = {
        keywords: String(edge.keywords || edge.description || ''),
        description: String(edge.description || ''),
        weight: edge.weight || 1,
        ...edge
      }
    })

    return { vertices, edges }
  }, [entities, hyperedges, t])

  const options = useMemo(() => {
    const hyperData = {
      nodes: [],
      edges: []
    }
    const plugins = []

    if (convertedData) {
      // 添加顶点
      for (const key in convertedData.vertices) {
        hyperData.nodes.push({
          ...convertedData.vertices[key],
          id: key,
          label: String(key) // 确保label是字符串
        })
      }

      if (mode === 'graph') {
        // graph模式：设置标准边格式，不使用plugins
        const edgeKeys = Object.keys(convertedData.edges)
        for (let i = 0; i < edgeKeys.length; i++) {
          const key = edgeKeys[i]
          const nodes = key.split('|#|')

          // 为每对节点创建边
          for (let j = 0; j < nodes.length; j++) {
            for (let k = j + 1; k < nodes.length; k++) {
              hyperData.edges.push({
                source: nodes[j],
                target: nodes[k],
                ...convertedData.edges[key]
              })
            }
          }
        }
      } else {
        // hyper模式：使用原有的bubble-sets插件
        // 创建样式函数
        const createStyle = baseColor => ({
          fill: baseColor,
          stroke: baseColor,
          labelFill: '#fff',
          labelPadding: 2,
          labelBackgroundFill: baseColor,
          labelBackgroundRadius: 5,
          labelPlacement: 'center',
          labelAutoRotate: false,
          // bubblesets配置
          maxRoutingIterations: 100,
          maxMarchingIterations: 20,
          pixelGroup: 4,
          edgeR0: 10,
          edgeR1: 60,
          nodeR0: 15,
          nodeR1: 50,
          morphBuffer: 10,
          threshold: 4,
          memberInfluenceFactor: 1,
          edgeInfluenceFactor: 4,
          nonMemberInfluenceFactor: -0.8,
          virtualEdges: true
        })

        // 添加超边
        const edgeKeys = Object.keys(convertedData.edges)
        for (let i = 0; i < edgeKeys.length; i++) {
          const key = edgeKeys[i]
          const edge = convertedData.edges[key]
          const nodes = key.split('|#|')

          plugins.push({
            key: `bubble-sets-${key}`,
            type: 'bubble-sets',
            members: nodes,
            // labelText: String(edge.keywords || ''), // 确保labelText是字符串
            ...createStyle(colors[i % colors.length])
          })
        }
      }

      // 添加tooltip插件
      if (showTooltip) {
        plugins.push({
          type: 'tooltip',
          getContent: (e, items) => {
            let result = ''
            items.forEach(item => {
              result += `<h4>${String(item.id)}</h4>`
              if (item.entity_type) {
                result += `<p><strong>${t('retrieval.entity_type')}:</strong> ${String(
                  item.entity_type
                )}</p>`
              }
              if (item.description) {
                const desc = String(item.description)
                result += `<p><strong>${t('retrieval.description')}:</strong> ${desc
                  .split('<SEP>')
                  .slice(0, 2)
                  .join('; ')}</p>`
              }
            })
            return result
          }
        })
      }
    }

    return {
      autoResize: true,
      data: hyperData,
      node: {
        palette: { field: 'cluster' },
        style: {
          size: mode === 'graph' ? 20 : 25,
          labelText: d => d.id,
          fill: d => {
            // 根据entity_type设置不同颜色
            if (d.entity_type) {
              return entityTypeColors[d.entity_type] || '#8566CC'
            }
            // 默认颜色
            return '#8566CC'
          }
        }
      },
      edge: {
        style: {
          stroke: '#a68fff', // 边的颜色
          lineWidth: 3
        }
      },
      animate: false,
      behaviors: ['zoom-canvas', 'drag-canvas', 'drag-element'],
      autoFit: { type: 'view' as const },
      layout: {
        type: 'force-atlas2',
        // clustering: true,
        preventOverlap: true,
        // nodeClusterBy: 'entity_type',
        kr: mode === 'graph' ? 5 : 80,
        gravity: 20,
        linkDistance: 10
      },
      plugins: mode === 'graph' ? (showTooltip ? plugins : []) : plugins
    }
  }, [convertedData, showTooltip, mode, t])

  // 如果没有数据，不显示组件
  if (!convertedData || (!entities.length && !hyperedges.length)) {
    return null
  }

  return (
    <div style={{ height, width, ...containerStyle }}>
      <div
        style={{
          marginBottom: '8px',
          fontSize: '14px',
          color: '#666',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}
      >
        <span>
          {t('retrieval.title')} - {mode}
        </span>
        <span style={{ fontSize: '12px' }}>
          {edgesName}: {hyperedges.length}
        </span>
      </div>
      <Graphin
        options={options}
        id={graphId}
        style={{
          width: '100%',
          height: 'calc(100% - 30px)',
          border: '1px solid #e0e0e0',
          borderRadius: '6px'
        }}
      />
    </div>
  )
}

export default RetrievalHyperGraph
