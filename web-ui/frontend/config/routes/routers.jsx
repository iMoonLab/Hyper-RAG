import NotFoundPage from '@/404'
import App from '@/App'
import ErrorPage from '@/ErrorPage'
import Home from '@/pages/Home'
import Files from '@/pages/Hyper/Files'
import Graph from '@/pages/Hyper/Graph'
import { HomeFilled, SmileFilled, FileAddOutlined, QuestionCircleOutlined, DeploymentUnitOutlined, DatabaseOutlined, SettingOutlined } from '@ant-design/icons'
import { Navigate } from 'react-router-dom'

export const routers = [
  {
    path: '/',
    element: <Navigate replace to="/Hyper/show" />
  },
  {
    path: '/',
    element: <App />,
    errorElement: <ErrorPage />,
    icon: <SmileFilled />,
    children: [

      {
        path: '/Hyper/qa',
        name: 'Chat',
        icon: <QuestionCircleOutlined />,
        // permissionObj: true,
        element: <Home />
      },
      {
        path: '/Hyper/show',
        name: 'Hypergraph Visualization',
        icon: <DeploymentUnitOutlined />,
        // permissionObj: true,
        element: <Graph />
      },
      {
        path: '/Hyper/files',
        name: 'Upload Documents',
        icon: <FileAddOutlined />,
        element: <Files />,
      },
      // {
      //   path: '/Hyper/DB',
      //   name: 'HypergraphDB',
      //   icon: <DatabaseOutlined />,
      //   // permissionObj: true,
      //   element: <Home />
      // },
      {
        path: '/Setting',
        name: 'Key Setting',
        icon: <SettingOutlined />,
        // permissionObj: true,
        element: <Home />
      },
    ]
  },
  { path: '*', element: <NotFoundPage /> }
]
