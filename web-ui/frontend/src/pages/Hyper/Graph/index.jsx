import React, { useEffect, useMemo, useState } from 'react';
import { Graphin } from '@antv/graphin';

import { Select, Card, Tag } from 'antd';

const SERVER_URL = import.meta.env.VITE_SERVER_URL;

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
]

export default () => {
  const [data, setData] = useState(undefined);
  const [keys, setKeys] = useState(undefined);
  const [key, setKey] = useState(undefined);
  const [item, setItem] = useState({
    entity_name: '',
    entity_type: '',
    descriptions: [''],
    properties: ['']
  });
  const [mode,setMode] = useState('node');

  useEffect(() => {
    fetch(SERVER_URL + '/db/vertices')
      .then((res) => res.json())
      .then((data) => {
        setKeys(data);
      }
      )
    fetch(SERVER_URL + '/db/vertices_neighbor/' + '刘伯钦')
      .then((res) => res.json())
      .then((data) => {
        setData(data);
        const item = data.vertices['刘伯钦'];
        setItem({
          entity_name: item.entity_name,
          entity_type: item.entity_type,
          descriptions: item.description.split('<SEP>'),
          properties: item.additional_properties.split('<SEP>')
        });
      }
      )
  }, [mode]);
  useEffect(() => {
    if (mode==='hyperedge'){
      fetch(SERVER_URL + '/db/hyperedges')
        .then((res) => res.json())
        .then((data) => {
          setKeys(data);
        }
        )
      fetch(SERVER_URL + '/db/hyperedge_neighbor/' + '二郎神')
        .then((res) => res.json())
        .then((data) => {
          setData(data);
        }
        )
      }
  }, [mode]);
  useEffect(() => {
    if (!key) return;
    fetch(SERVER_URL + '/db/vertices_neighbor/' + key)
      .then((res) => res.json())
      .then((data) => {
        setData(data);
        const item = data.vertices[key];
        setItem({
          entity_name: item.entity_name,
          entity_type: item.entity_type,
          descriptions: item.description.split('<SEP>'),
          properties: item.additional_properties.split('<SEP>')
        });
      }
      )
  }, [key]);
  const handleAfterRender = (graph) => {
    // 遍历所有节点并将它们放到最上层
    graph.getNodes().forEach((node) => {
      graph.toFront(node); // 将节点放到最上层
    });
  
    // 确保 labelText 也显示在最上层
    graph.getNodes().forEach((node) => {
      const labelShape = node.get('group').find((element) => element.get('name') === 'text-shape');
      if (labelShape) {
        labelShape.toFront(); // 将 labelText 放到最上层
      }
    });
  };
  const handleNodeClick = (event) => {
    if (mode === 'node') {
      const { id } = event.item.getModel();
      setKey(id);
    }
  };
  const handleHyperedgeClick = (event) => {
    if (mode === 'hyperedge') {
      const { labelText } = event.item.getModel();
      console.log('Selected Hyperedge:', labelText);
    }
  };  
  const options = useMemo(
    () => {
      let groupedNodesByCluster = {};
      let createStyle = () => ({});

      let hyperData = {
        nodes: [],
        edges: [],
      };
      let plugins = [];
      if (data) {
        for (const key in data.vertices) {
          hyperData.nodes.push({
            id: key,
            label: key,
            style: {
              fill: '#4B0082', // 设置为紫色
              stroke: '#4B0082', // 边框也为紫色
              zIndex: 999, // 设置 z-index 为 999，保证节点在最上层
            },

            ...data.vertices[key],
          });
        }

        createStyle = (baseColor) => ({
          fill: baseColor,
          stroke: baseColor,
          labelFill: '#fff',
          labelPadding: 2,
          labelBackgroundFill: baseColor,
          labelBackgroundRadius: 5,
          labelPlacement: 'center',
          labelAutoRotate: false,
          // bubblesets
          maxRoutingIterations: 100,
          maxMarchingIterations: 20,
          pixelGroup: 4,
          edgeR0: 10,
          edgeR1: 60,
          nodeR0: 15,
          nodeR1: 50,
          morphBuffer: 10,
          threshold: 1,
          memberInfluenceFactor: 1,
          edgeInfluenceFactor: 1,
          nonMemberInfluenceFactor: -0.8,
          virtualEdges: true,
          zIndex:-1,
        });

        const keys = Object.keys(data.edges);
        for (let i = 0; i < keys.length; i++) {
          const key = keys[i];
          const edge = data.edges[key];
          const nodes = key.split('|#|');
          groupedNodesByCluster[key] = nodes;
          plugins.push({
            key: `bubble-sets-${key}`,
            type: 'bubble-sets',
            members: nodes,
            labelText: '' + edge.keywords,
            ...createStyle(colors[i % 10]),

          });
        }
      }

      plugins.push({
        type: 'tooltip',
        getContent: (e, items) => {
          let result = '';
          items.forEach((item) => {
            result += `<h4>${item.id}</h4><p>${item.description}</p>`;
          });
          return result;
        },
      })

      console.log(hyperData);

      return {
        autoResize: true,
        data: hyperData,
        node: {
          palette: { field: 'cluster' },
          // style: {
          //   fill: '#800080', // 所有节点填充色为紫色
          //   stroke: '#800080', // 所有节点边框色为紫色
          //   labelFill: '#fff', // 标签文字颜色（白色）
          //   labelPadding: 2,
          //   labelBackgroundFill: '#800080', // 标签背景色
          //   labelBackgroundRadius: 5,
          //   labelPlacement: 'center',
          //   labelAutoRotate: false,
          // },
          style: {
            labelText: d => d.id,
            zIndex:999,
          }
        },
        animate: false,
        behaviors: [
          // {
          //   type: 'click-select',
          //   degree: 1,
          //   state: 'active',
          //   unselectedState: 'inactive',
          //   multiple: true,
          //   trigger: ['shift'],
          // },
          'zoom-canvas', 'drag-canvas', 'drag-element',
        ],
        autoFit: 'center',
        layout: {
          type: 'force',
          // enableWorker: true,
          clustering: true,
          preventOverlap: true,
          // linkDistance: 700,
          nodeClusterBy: 'entity_type',
          gravity: 20
        },
        plugins,
      }
    },
    [data],
  );

  if (!data) return <p>Loading...</p>;

  return <>
  Focuse on <></>
    <Select
    value={mode}
    onChange={(value) => setMode(value)}
    style={{ width: 150 }}
  >
    <Select.Option value="node">Entity</Select.Option>
    <Select.Option value="hyperedge">Relation</Select.Option>
  </Select> 
  <> </>
    <Select onChange={setKey} style={{ width: 300 }} defaultValue={'刘伯钦'} showSearch>
      {keys.map((key) => {
        return <Select.Option key={key} value={key} >{key}</Select.Option>
      })}
    </Select>
    <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between' }}>
      <Graphin options={options} id="my-graphin-demo"
      className="my-graphin-container"
        style={{ width: '100%', height: '80vh' }} 
        onNodeClick={handleNodeClick}
        onEdgeClick={handleHyperedgeClick}
        onAfterRender={(graph) => handleAfterRender(graph)} // 在渲染完成后调整层级
        />

      <Card
        title={item.entity_name}
        style={{ width: 400, margin: '20px' }}
      >
        <div>
          <p><strong>类型:</strong> {item.entity_type}</p>

          <div style={{ margin: '10px 0' }}>
            <strong>描述:</strong>
            {item.descriptions?.map((desc, index) => (
              <p key={index}>{desc}</p>
            ))}
          </div>

          <div style={{ margin: '10px 0' }}>
            <strong>特征:</strong>
            <div style={{ marginTop: '8px' }}>
              {item.properties?.map((prop, index) => (
                <Tag key={index} color="blue" style={{ margin: '4px' }}>
                  {prop}
                </Tag>
              ))}
            </div>
          </div>
        </div>
      </Card>
    </div>
  </>
}