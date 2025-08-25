import React, { useState, useEffect } from 'react'
import {
  Card,
  Form,
  Input,
  Select,
  Button,
  message,
  Space,
  Divider,
  Typography,
  Alert,
  Row,
  Col,
  AutoComplete,
  Checkbox
} from 'antd'
import {
  SettingOutlined,
  KeyOutlined,
  DatabaseOutlined,
  ApiOutlined,
  SaveOutlined,
  ReloadOutlined,
  GlobalOutlined,
  AppstoreOutlined
} from '@ant-design/icons'
import { useTranslation } from 'react-i18next'
import LanguageSelector from '../../components/LanguageSelector'
import { SERVER_URL } from '../../utils'

const { Title, Text } = Typography
const { Option } = Select
const { Password } = Input

const Setting: React.FC = () => {
  const { t } = useTranslation()
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [saveLoading, setSaveLoading] = useState(false)
  const [availableDatabases, setAvailableDatabases] = useState<any[]>([])
  const [testResults, setTestResults] = useState<any>({})

  // 默认配置
  const defaultSettings = {
    apiKey: '',
    modelProvider: 'openai',
    modelName: 'gpt-3.5-turbo',
    baseUrl: 'https://api.openai.com/v1',
    selectedDatabase: '',
    maxTokens: 2000,
    temperature: 0.7,
    // 新增Mode配置，默认显示所有modes
    availableModes: ['llm', 'naive', 'graph', 'hyper', 'hyper-lite']
  }

  // 可用的查询模式配置
  const queryModes = [
    { value: 'llm', label: 'LLM', icon: '🤖', description: '仅使用大语言模型直接回答' },
    { value: 'naive', label: 'RAG', icon: '📚', description: '基础检索增强生成' },
    { value: 'graph', label: 'Graph-RAG', icon: '🕸️', description: '基于图结构的检索增强生成' },
    { value: 'hyper', label: 'Hyper-RAG', icon: '⚡', description: '基于超图的检索增强生成' },
    {
      value: 'hyper-lite',
      label: 'Hyper-RAG-Lite',
      icon: '🔸',
      description: '轻量级超图检索增强生成'
    }
  ]

  // 模型提供商配置
  const modelProviders = [
    {
      value: 'openai',
      label: 'OpenAI',
      models: ['gpt-5', 'gpt-5-mini', 'gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
      defaultBaseUrl: 'https://api.openai.com/v1'
    },
    {
      value: 'azure',
      label: 'Azure OpenAI',
      models: ['gpt-5', 'gpt-5-mini', 'gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
      defaultBaseUrl: 'https://your-resource.openai.azure.com'
    },
    {
      value: 'anthropic',
      label: 'Anthropic',
      models: ['claude-4-haiku', 'claude-4-sonnet', 'claude-4-opus'],
      defaultBaseUrl: 'https://api.anthropic.com'
    },
    {
      value: 'custom',
      label: t('settings.custom_api') || '自定义API',
      models: ['custom-model'],
      defaultBaseUrl: 'http://localhost:11434'
    }
  ]

  // 加载设置
  const loadSettings = async () => {
    setLoading(true)
    try {
      // 首先尝试从localStorage加载Mode配置
      const localModeSettings = localStorage.getItem('hyperrag_mode_settings')
      let modeSettings = {}
      if (localModeSettings) {
        try {
          modeSettings = JSON.parse(localModeSettings)
        } catch (e) {
          console.error('解析本地Mode设置失败:', e)
        }
      }

      const response = await fetch(`${SERVER_URL}/settings`)
      if (response.ok) {
        const settings = await response.json()
        form.setFieldsValue({ ...defaultSettings, ...settings, ...modeSettings })
      } else {
        // 如果获取失败，使用默认设置加上本地Mode设置
        form.setFieldsValue({ ...defaultSettings, ...modeSettings })
      }
    } catch (error) {
      console.error('加载设置失败:', error)
      // 尝试加载本地Mode设置
      const localModeSettings = localStorage.getItem('hyperrag_mode_settings')
      let modeSettings = {}
      if (localModeSettings) {
        try {
          modeSettings = JSON.parse(localModeSettings)
        } catch (e) {
          console.error('解析本地Mode设置失败:', e)
        }
      }
      form.setFieldsValue({ ...defaultSettings, ...modeSettings })
      message.warning(t('settings.load_failed'))
    } finally {
      setLoading(false)
    }
  }

  // 加载可用数据库列表
  const loadDatabases = async () => {
    try {
      const response = await fetch(`${SERVER_URL}/databases`)
      if (response.ok) {
        const databases = await response.json()
        setAvailableDatabases(databases)
      }
    } catch (error) {
      console.error('加载数据库列表失败:', error)
      // 如果API不存在，提供一些默认选项
      setAvailableDatabases([
        { name: 'hypergraph_wukong', description: '西游记超图' },
        { name: 'hypergraph_A_Christmas_Carol', description: '圣诞颂歌超图' }
      ])
    }
  }

  // 保存设置
  const saveSettings = async (values: any) => {
    setSaveLoading(true)
    try {
      // 分离Mode设置和其他设置
      const { availableModes, ...otherSettings } = values

      // Mode设置保存到localStorage
      const modeSettings = { availableModes }
      localStorage.setItem('hyperrag_mode_settings', JSON.stringify(modeSettings))

      const response = await fetch(`${SERVER_URL}/settings`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(otherSettings)
      })

      if (response.ok) {
        message.success(t('settings.save_success'))
        // 保存到本地存储作为备份
        localStorage.setItem('hyperrag_settings', JSON.stringify(otherSettings))
      } else {
        throw new Error(t('settings.save_failed'))
      }
    } catch (error) {
      console.error('保存设置失败:', error)
      // 即使后端保存失败，也保存到本地存储
      const { availableModes, ...otherSettings } = values
      localStorage.setItem('hyperrag_settings', JSON.stringify(otherSettings))
      localStorage.setItem('hyperrag_mode_settings', JSON.stringify({ availableModes }))
      message.warning(t('settings.backend_save_failed'))
    } finally {
      setSaveLoading(false)
    }
  }

  // 测试API连接
  const testAPIConnection = async () => {
    const values = form.getFieldsValue()
    if (!values.apiKey) {
      message.error(t('settings.api_key_required'))
      return
    }

    setTestResults({ ...testResults, api: 'testing' })
    try {
      const response = await fetch(`${SERVER_URL}/test-api`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          apiKey: values.apiKey,
          baseUrl: values.baseUrl,
          modelName: values.modelName,
          modelProvider: values.modelProvider
        })
      })

      if (response.ok) {
        const result = await response.json()
        setTestResults({ ...testResults, api: 'success' })
        message.success(t('settings.api_test_success'))
      } else {
        setTestResults({ ...testResults, api: 'failed' })
        message.error(t('settings.api_test_failed'))
      }
    } catch (error: any) {
      setTestResults({ ...testResults, api: 'failed' })
      message.error(t('settings.api_test_failed') + ': ' + error.message)
    }
  }

  // 测试数据库连接
  const testDatabaseConnection = async () => {
    const values = form.getFieldsValue()
    if (!values.selectedDatabase) {
      message.error(t('settings.database_required'))
      return
    }

    setTestResults({ ...testResults, database: 'testing' })
    try {
      const response = await fetch(`${SERVER_URL}/test-database`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          database: values.selectedDatabase
        })
      })

      if (response.ok) {
        setTestResults({ ...testResults, database: 'success' })
        message.success(t('settings.database_test_success'))
      } else {
        setTestResults({ ...testResults, database: 'failed' })
        message.error(t('settings.database_test_failed'))
      }
    } catch (error: any) {
      setTestResults({ ...testResults, database: 'failed' })
      message.error(t('settings.database_test_failed') + ': ' + error.message)
    }
  }

  // 重置设置
  const resetSettings = () => {
    form.setFieldsValue(defaultSettings)
    setTestResults({})
    // 也清除localStorage中的Mode设置
    localStorage.removeItem('hyperrag_mode_settings')
    message.info(t('settings.reset_success'))
  }

  // 监听模型提供商变化
  const handleProviderChange = (value: string) => {
    const provider = modelProviders.find(p => p.value === value)
    if (provider) {
      form.setFieldsValue({
        baseUrl: provider.defaultBaseUrl,
        modelName: provider.models[0] // 设置默认模型，用户仍可输入自定义模型
      })
    }
  }

  useEffect(() => {
    loadSettings()
    loadDatabases()
  }, [])

  return (
    <div className="m-2">
      <Card>
        <div className="mb-4">
          <div className="flex items-center text-2xl font-bold">
            <SettingOutlined style={{ marginRight: '8px' }} />
            {t('settings.title')}
          </div>
          <Text type="secondary">{t('settings.subtitle')}</Text>
        </div>

        <Form form={form} layout="vertical" onFinish={saveSettings} initialValues={defaultSettings}>
          {/* 系统配置区块 */}
          <Card
            title={
              <span>
                <GlobalOutlined style={{ marginRight: '8px' }} />
                {t('settings.system_config')}
              </span>
            }
            style={{ marginBottom: '24px' }}
          >
            <Form.Item label={t('settings.language_select')}>
              <LanguageSelector />
            </Form.Item>
          </Card>

          {/* API 配置区块 */}
          <Card
            title={
              <span>
                <ApiOutlined style={{ marginRight: '8px' }} />
                {t('settings.api_config')}
              </span>
            }
            style={{ marginBottom: '24px' }}
          >
            <Alert
              message={t('settings.api_config')}
              description={t('settings.api_description')}
              type="info"
              showIcon
              style={{ marginBottom: '24px' }}
            />

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="modelProvider"
                  label={t('settings.model_provider')}
                  rules={[{ required: true, message: t('settings.provider_required') }]}
                >
                  <Select onChange={handleProviderChange}>
                    {modelProviders.map(provider => (
                      <Option key={provider.value} value={provider.value}>
                        {provider.label}
                      </Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="modelName"
                  label={t('settings.model_name')}
                  rules={[{ required: true, message: t('settings.model_required') }]}
                  extra={t('settings.model_name_help')}
                >
                  <AutoComplete
                    placeholder={t('settings.model_name_placeholder')}
                    allowClear
                    filterOption={(inputValue, option) =>
                      option!.value.toLowerCase().includes(inputValue.toLowerCase())
                    }
                    options={
                      form.getFieldValue('modelProvider')
                        ? modelProviders
                            .find(p => p.value === form.getFieldValue('modelProvider'))
                            ?.models.map(model => ({
                              value: model,
                              label: model
                            })) || []
                        : []
                    }
                  />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="baseUrl"
              label={t('settings.api_base_url')}
              rules={[{ required: true, message: t('settings.base_url_required') }]}
            >
              <Input placeholder="https://api.openai.com/v1" />
            </Form.Item>

            <Form.Item
              name="apiKey"
              label={t('settings.api_key')}
              rules={[{ required: true, message: t('settings.api_key_required') }]}
            >
              <Password
                placeholder={t('settings.api_key_placeholder')}
                iconRender={visible => (visible ? <KeyOutlined /> : <KeyOutlined />)}
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="maxTokens"
                  label={t('settings.max_tokens')}
                  rules={[{ required: true, message: t('settings.max_tokens_required') }]}
                >
                  <Input type="number" min={1} max={8000} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="temperature"
                  label={t('settings.temperature')}
                  rules={[{ required: true, message: t('settings.temperature_required') }]}
                >
                  <Input type="number" min={0} max={2} step={0.1} />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item>
              <Button
                type="default"
                onClick={testAPIConnection}
                loading={testResults.api === 'testing'}
                style={{ marginRight: '8px' }}
              >
                {t('settings.test_api_connection')}
              </Button>
              {testResults.api === 'success' && (
                <Text type="success">{t('settings.connection_success')}</Text>
              )}
              {testResults.api === 'failed' && (
                <Text type="danger">{t('settings.connection_failed')}</Text>
              )}
            </Form.Item>
          </Card>

          {/* Mode配置区块 */}
          <Card
            title={
              <span>
                <AppstoreOutlined style={{ marginRight: '8px' }} />
                查询模式配置
              </span>
            }
            style={{ marginBottom: '24px' }}
          >
            <Alert
              message="查询模式配置"
              description="选择在聊天界面中显示的查询模式。配置将保存在本地浏览器中。"
              type="info"
              showIcon
              style={{ marginBottom: '24px' }}
            />

            <Form.Item
              name="availableModes"
              label="可用的查询模式"
              extra="选择在聊天界面侧边栏中显示的查询模式"
            >
              <Checkbox.Group style={{ width: '100%' }}>
                <Row gutter={[16, 16]}>
                  {queryModes.map(mode => (
                    <Col span={12} key={mode.value}>
                      <Card size="small" style={{ height: '100%' }}>
                        <Checkbox value={mode.value} style={{ width: '100%' }}>
                          <div style={{ marginLeft: '8px' }}>
                            <div style={{ fontWeight: 'bold', fontSize: '14px' }}>
                              <span style={{ marginRight: '6px' }}>{mode.icon}</span>
                              {mode.label}
                            </div>
                            <div style={{ fontSize: '12px', color: '#666', marginTop: '4px' }}>
                              {mode.description}
                            </div>
                          </div>
                        </Checkbox>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Checkbox.Group>
            </Form.Item>
          </Card>

          {/* 数据库配置区块 */}
          {/* <Card
            title={
              <span>
                <DatabaseOutlined style={{ marginRight: '8px' }} />
                {t('settings.database_config')}
              </span>
            }
            style={{ marginBottom: '24px' }}
          >
            <Alert
              message={t('settings.database_config')}
              description={t('settings.database_description')}
              type="info"
              showIcon
              style={{ marginBottom: '24px' }}
            />

            <Form.Item
              name="selectedDatabase"
              label={t('settings.select_database')}
              rules={[{ required: true, message: t('settings.database_selection_required') }]}
            >
              <Select placeholder={t('settings.select_database_placeholder')} loading={loading}>
                {availableDatabases.map(db => (
                  <Option key={db.name} value={db.name}>
                    <div>
                      <div style={{ fontWeight: 'bold' }}>{db.name}</div>
                      {db.description && (
                        <div style={{ fontSize: '12px', color: '#666' }}>{db.description}</div>
                      )}
                    </div>
                  </Option>
                ))}
              </Select>
            </Form.Item>

            <Form.Item>
              <Button
                type="default"
                onClick={testDatabaseConnection}
                loading={testResults.database === 'testing'}
                style={{ marginRight: '8px' }}
              >
                {t('settings.test_database_connection')}
              </Button>
              {testResults.database === 'success' && (
                <Text type="success">{t('settings.connection_success')}</Text>
              )}
              {testResults.database === 'failed' && (
                <Text type="danger">{t('settings.connection_failed')}</Text>
              )}
            </Form.Item>
          </Card> */}

          <Divider />

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<SaveOutlined />}
                loading={saveLoading}
              >
                {t('settings.save_settings')}
              </Button>
              <Button type="default" onClick={resetSettings} icon={<ReloadOutlined />}>
                {t('settings.reset_settings')}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  )
}

export default Setting
