import React, { useEffect, useMemo, useState } from 'react';
import { Graphin } from '@antv/graphin';
import { Spin, message } from 'antd';

const SERVER_URL = import.meta.env.VITE_SERVER_URL || 'http://localhost:8000';

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
    '#c8ff00',
];

const entityTypeColors = {
    'PERSON': '#00C9C9',
    'CONCEPT': '#a68fff',
    'ORGANIZATION': '#F08F56',
    'LOCATION': '#16f69c',
    'EVENT': '#004ac9',
    'PRODUCT': '#f056d1',
}

const HyperGraph = ({
    vertexId,
    database,
    height = '400px',
    width = '100%',
    showTooltip = true,
    containerStyle = {},
    graphId = 'hypergraph-viewer'
}) => {
    const [data, setData] = useState(undefined);
    const [loading, setLoading] = useState(false);

    // 获取vertex邻居数据
    const fetchVertexNeighbor = async (vId, db) => {
        if (!vId) return;

        setLoading(true);
        try {
            const url = db
                ? `${SERVER_URL}/db/vertices_neighbor/${encodeURIComponent(vId)}?database=${encodeURIComponent(db)}`
                : `${SERVER_URL}/db/vertices_neighbor/${encodeURIComponent(vId)}`;

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`API failed: ${response.status}`);
            }
            const neighborData = await response.json();
            setData(neighborData);
        } catch (error) {
            console.error('Failed to fetch vertex neighbor:', error);
            message.error(`获取图数据失败: ${error.message}`);
        }
        setLoading(false);
    };

    useEffect(() => {
        if (vertexId) {
            fetchVertexNeighbor(vertexId, database);
        }
    }, [vertexId, database]);

    const options = useMemo(() => {
        let hyperData = {
            nodes: [],
            edges: [],
        };
        let plugins = [];

        if (data) {
            // 添加顶点
            for (const key in data.vertices) {
                hyperData.nodes.push({
                    id: key,
                    label: key,
                    ...data.vertices[key],
                });
            }

            // 创建样式函数
            const createStyle = (baseColor) => ({
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
                virtualEdges: true,
            });

            // 添加超边
            const edgeKeys = Object.keys(data.edges);
            for (let i = 0; i < edgeKeys.length; i++) {
                const key = edgeKeys[i];
                const edge = data.edges[key];
                const nodes = key.split('|#|');

                plugins.push({
                    key: `bubble-sets-${key}`,
                    type: 'bubble-sets',
                    members: nodes,
                    labelText: edge.keywords || '',
                    ...createStyle(colors[i % colors.length]),
                });
            }

            // 添加tooltip插件
            if (showTooltip) {
                plugins.push({
                    type: 'tooltip',
                    getContent: (e, items) => {
                        let result = '';
                        items.forEach((item) => {
                            result += `<h4>${item.id}</h4>`;
                            if (item.entity_type) {
                                result += `<p><strong>类型:</strong> ${item.entity_type}</p>`;
                            }
                            if (item.description) {
                                result += `<p><strong>描述:</strong> ${item.description.split('<SEP>').slice(0, 2).join('；')}</p>`;
                            }
                        });
                        return result;
                    },
                });
            }
        }

        return {
            autoResize: true,
            data: hyperData,
            node: {
                palette: { field: 'cluster' },
                style: {
                    size: 25,
                    labelText: d => d.id,
                    fill: d => {
                        // 如果是当前查看的顶点，使用红色高亮
                        if (d.id === vertexId) {
                            return 'black';
                        }
                        // 根据entity_type设置不同颜色
                        if (d.entity_type) {
                            return entityTypeColors[d.entity_type] || '#8566CC' ;
                        }
                        // 默认颜色
                        return '#8566CC';
                    },
                }
            },
            edge: {
                style: {
                    size: 2,
                }
            },
            animate: false,
            behaviors: [
                'zoom-canvas',
                'drag-canvas',
                'drag-element',
            ],
            autoFit: 'center',
            layout: {
                type: 'force',
                clustering: true,
                preventOverlap: true,
                nodeClusterBy: 'entity_type',
                gravity: 20,
                linkDistance: 150,
            },
            plugins,
        };
    }, [data, vertexId, showTooltip]);

    if (loading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height,
                ...containerStyle
            }}>
                <Spin size="large" tip="加载超图数据中..." />
            </div>
        );
    }

    if (!data || !vertexId) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height,
                color: '#999',
                ...containerStyle
            }}>
                {!vertexId ? '请选择一个顶点' : '暂无图数据'}
            </div>
        );
    }

    return (
        <div style={{ height, width, ...containerStyle }}>
            <Graphin
                options={options}
                id={graphId}
                style={{ width: '100%', height: '100%' }}
                error={() => {
                    return <div>
                        <div>

                        </div>
                    </div>
                }}
            />
        </div>
    );
};

export default HyperGraph; 