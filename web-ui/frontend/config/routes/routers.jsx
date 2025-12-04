import NotFoundPage from '@/404'
import App from '@/App'
import ErrorPage from '@/ErrorPage'
import Home from '@/pages/Home'
import Files from '@/pages/Hyper/Files'
import Graph from '@/pages/Hyper/Graph'
import HyperDB from '@/pages/Hyper/DB'
import Setting from '@/pages/Setting'
import APIPage from '@/pages/API'
import { HomeFilled, SmileFilled, FileAddOutlined, QuestionCircleOutlined, DeploymentUnitOutlined, DatabaseOutlined, SettingOutlined, ApiOutlined } from '@ant-design/icons'
import { Navigate } from 'react-router-dom'

export const routers = [
  {
    path: '/',
    element: <Navigate replace to="/Hyper/chat" />
  },
  {
    path: '/',
    element: <App />,
    errorElement: <ErrorPage />,
    icon: <SmileFilled />,
    children: [
      {
        path: '/Hyper/chat',
        name: '检索问答',
        icon: <QuestionCircleOutlined />,
        // permissionObj: true,
        element: <Home />
      },
      {
        path: '/Hyper/show',
        name: '超图展示',
        icon: <DeploymentUnitOutlined />,
        // permissionObj: true,
        element: <Graph />
      },
      // {
      //   path: '/Hyper/DB',
      //   name: 'HypergraphDB',
      //   icon: <DatabaseOutlined />,
      //   // permissionObj: true,
      //   element: <HyperDB />
      // },
      // {
      //   path: '/Hyper/files',
      //   name: '文档解析',
      //   icon: <FileAddOutlined />,
      //   element: <Files />,
      // },
      // {
      //   path: '/API',
      //   name: 'API 文档',
      //   icon: <ApiOutlined />,
      //   element: <APIPage />,
      // },
      // {
      //   path: '/Setting',
      //   name: '系统设置',
      //   icon: <SettingOutlined />,
      //   // permissionObj: true,
      //   element: <Setting />
      // },
    ]
  },
  { path: '*', element: <NotFoundPage /> }
]
