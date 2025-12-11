import React, { useEffect, useState } from 'react';
import { Select, Card, Tag, Spin } from 'antd';
import { observer } from 'mobx-react';
import { useTranslation } from 'react-i18next';
import { storeGlobalUser } from '../../../store/globalUser';
import HyperGraph from '../../../components/HyperGraph';
import DatabaseSelector from '../../../components/DatabaseSelector';
import { DatabaseOutlined } from '@ant-design/icons';
import { SERVER_URL } from '../../../utils';

const GraphPage = () => {
  const { t } = useTranslation();
  const [keys, setKeys] = useState(undefined);
  const [key, setKey] = useState(undefined);
  const [loading, setLoading] = useState(false);
  const [item, setItem] = useState({
    entity_name: '',
    entity_type: '',
    descriptions: [''],
    properties: ['']
  });
  const [verticesList, setVerticesList] = useState([]);
  const [verticesPage, setVerticesPage] = useState(1);
  const [verticesTotal, setVerticesTotal] = useState(0);
  const [verticesLoading, setVerticesLoading] = useState(false);

  // 初始化数据库
  useEffect(() => {
    storeGlobalUser.restoreSelectedDatabase();
    storeGlobalUser.loadDatabases();
  }, []);

  // 获取vertices分页加载
  const loadVertices = async (page = 1, append = false) => {
    setVerticesLoading(true);
    const pageSize = 32768;
    const url = `${SERVER_URL}/db/vertices?database=${encodeURIComponent(storeGlobalUser.selectedDatabase)}&page=${page}`;
    const res = await fetch(url);
    const data = await res.json();
    const list = data.data || data;
    setVerticesTotal(data.total || list.length);
    setVerticesPage(page);
    setVerticesList(prev => append ? [...prev, ...list] : list);
    setVerticesLoading(false);
  };

  // 获取vertices列表
  useEffect(() => {
    if (!storeGlobalUser.selectedDatabase) return;

    setLoading(true);
    const url = `${SERVER_URL}/db/vertices?database=${encodeURIComponent(storeGlobalUser.selectedDatabase)}`;
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        // 处理分页数据格式
        const vertices = data.data || data;
        setKeys(vertices);
        // 设置默认选中第一个vertex
        if (vertices && vertices.length > 0) {
          setKey(vertices[0]);
        }
        setLoading(false);
      })
      .catch((error) => {
        console.error(t('graph.fetch_vertices_failed') + ':', error);
        setLoading(false);
      });
  }, [storeGlobalUser.selectedDatabase, t]);

  // 初始化和数据库切换时加载第一页
  useEffect(() => {
    if (storeGlobalUser.selectedDatabase) {
      setVerticesList([]);
      setVerticesPage(1);
      setVerticesTotal(0);
      loadVertices(1, false);
    }
  }, [storeGlobalUser.selectedDatabase]);

  // 获取选中实体的详细信息（用于右侧详情展示）
  useEffect(() => {
    if (!key || !storeGlobalUser.selectedDatabase) return;

    const url = `${SERVER_URL}/db/vertices_neighbor/${encodeURIComponent(key)}?database=${encodeURIComponent(storeGlobalUser.selectedDatabase)}`;
    fetch(url)
      .then((res) => res.json())
      .then((data) => {
        const item = data.vertices[key];
        if (item) {
          setItem({
            entity_name: item.entity_name,
            entity_type: item.entity_type,
            descriptions: item.description ? item.description.split('<SEP>') : [''],
            properties: item.additional_properties ? item.additional_properties.split('<SEP>') : ['']
          });
        }
      })
      .catch((error) => {
        console.error(t('graph.fetch_neighbor_data_failed') + ':', error);
      });
  }, [key, storeGlobalUser.selectedDatabase, t]);

  // 数据库切换处理
  const onDatabaseChange = () => {
    // 清空选择
    setKey(undefined);
    setItem({
      entity_name: '',
      entity_type: '',
      descriptions: [''],
      properties: ['']
    });
  };

  // 渲染加载状态
  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <Spin size="large" />
        <div>{t('graph.loading_data')}</div>
      </div>
    );
  }

  // 渲染未选择数据库状态
  if (!storeGlobalUser.selectedDatabase) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <DatabaseOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
        <Spin size="large" />
        <div>正在加载数据库...</div>
      </div>
    );
  }

  // 渲染无数据状态
  if (!keys || keys.length === 0) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '400px',
        flexDirection: 'column',
        gap: '16px'
      }}>
        <DatabaseOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />
        <div>{t('graph.no_entity_data')}</div>
        <div style={{ color: '#999' }}>{t('graph.database_label')}: {storeGlobalUser.selectedDatabase}</div>
        <div style={{ color: 'red', marginTop: 10 }}>当前数据库为空或加载失败，请检查后端数据。</div>
      </div>
    );
  }

  return (
    <>
      <div className='m-4' style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 5 }}>
        {/* <span>{t('graph.hypergraph_database')}</span>
        <DatabaseSelector
          mode="compact"
          showRefresh={false}
          size="middle"
          onChange={onDatabaseChange}
        /> */}

        <span className='ml-4'>{t('graph.select_entity')}</span>
        <Select
          value={key}
          style={{ width: 300 }}
          showSearch
          loading={verticesLoading}
          placeholder={t('graph.select_entity_placeholder')}
          onChange={setKey}
          onPopupScroll={e => {
            const target = e.target;
            if (target.scrollTop + target.offsetHeight >= target.scrollHeight - 10) {
              if (verticesList.length < verticesTotal && !verticesLoading) {
                loadVertices(verticesPage + 1, true);
              }
            }
          }}
          filterOption={(input, option) =>
            (option?.value ?? '').toLowerCase().includes(input.toLowerCase())
          }
        >
          {(Array.isArray(verticesList) ? verticesList : []).map(vertexKey => (
            <Select.Option key={vertexKey} value={vertexKey}>
              {vertexKey}
            </Select.Option>
          ))}
        </Select>
      </div>

      <div style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between' }}>
        {/* 使用HyperGraph组件展示超图 */}
        <div style={{ width: '70%' }}>
          <HyperGraph
            vertexId={key}
            database={storeGlobalUser.selectedDatabase}
            height="calc(100vh - 100px)"
            width="100%"
            showTooltip={true}
            graphId="graph-page-hypergraph"
          />
        </div>

        {/* 实体详情卡片 */}
        <Card 
          title={t('graph.entity_details')}
          style={{ width: '28%', height: '600px', overflow: 'auto' }}
        >
          <p><strong>{t('graph.entity_name')}:</strong> {item.entity_name}</p>
          <p><strong>{t('graph.entity_type')}:</strong> <Tag color="blue">{item.entity_type}</Tag></p>
          <p><strong>{t('graph.description')}:</strong></p>
          <ul>
            {item.descriptions.map((desc, idx) => (
              <li key={idx}>{desc}</li>
            ))}
          </ul>
          <p><strong>{t('graph.properties')}:</strong></p>
          <ul>
            {item.properties.map((prop, idx) => (
              <li key={idx}>{prop}</li>
            ))}
          </ul>
        </Card>
      </div>
    </>
  );
};

export default observer(GraphPage);