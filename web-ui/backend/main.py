from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from db import get_hypergraph, getFrequentVertices, get_vertices, get_hyperedges, get_vertice, get_vertice_neighbor, get_hyperedge_neighbor_server, add_vertex, add_hyperedge, delete_vertex, delete_hyperedge, update_vertex, update_hyperedge, get_hyperedge_detail, db_manager
from file_manager import file_manager
import json
import os
import asyncio
import numpy as np
import logging
import sys
import importlib.util
from pathlib import Path
from pydantic import BaseModel
from typing import List
from io import StringIO

# 添加 HyperRAG 相关导入
# 若尚不可导入，则向上逐级查找含有 hyperrag 包的目录，并把“其父目录”加到 sys.path
if importlib.util.find_spec("hyperrag") is None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "hyperrag" / "__init__.py").exists():
            sys.path.insert(0, str(parent))  # 注意是父目录，不是 …/hyperrag
            break

try:
    from hyperrag import HyperRAG, QueryParam
    from hyperrag.utils import EmbeddingFunc
    from hyperrag.llm import openai_embedding, openai_complete_if_cache
    HYPERRAG_AVAILABLE = True
except ImportError as e:
    print(f"HyperRAG not available: {e}")
    HYPERRAG_AVAILABLE = False


# 设置文件路径
SETTINGS_FILE = "settings.json"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Hyper-RAG"}


@app.get("/db")
async def db(database: str = None):
    """
    获取全部数据json
    """
    try:
        data = get_hypergraph(database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/vertices")
async def get_vertices_function(database: str = None, page: int = None, page_size: int = None):
    """
    获取vertices列表
    """
    try:
        data = getFrequentVertices(database, page, page_size)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/hyperedges")
async def get_hypergraph_function(database: str = None, page: int = None, page_size: int = None):
    """
    获取hyperedges列表
    """
    try:
        data = get_hyperedges(database, page, page_size)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/hyperedges/{hyperedge_id}")
async def get_hyperedge(hyperedge_id: str, database: str = None):
    """
    获取指定hyperedge的详情
    """
    try:
        hyperedge_id = hyperedge_id.replace("%20", " ")
        vertices = hyperedge_id.split("|*|")
        data = get_hyperedge_detail(vertices, database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/vertices/{vertex_id}")
async def get_vertex(vertex_id: str, database: str = None):
    """
    获取指定vertex的json
    """
    vertex_id = vertex_id.replace("%20", " ")
    try:
        data = get_vertice(vertex_id, database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/vertices_neighbor/{vertex_id}")
async def get_vertex_neighbor(vertex_id: str, database: str = None):
    """
    获取指定vertex的neighbor
    """
    vertex_id = vertex_id.replace("%20", " ")
    try:
        data = get_vertice_neighbor(vertex_id, database)
        return data
    except Exception as e:
        return {"error": str(e)}

@app.get("/db/hyperedge_neighbor/{hyperedge_id}")
async def get_hyperedge_neighbor(hyperedge_id: str, database: str = None):
    """
    获取指定hyperedge的neighbor
    """
    hyperedge_id = hyperedge_id.replace("%20", " ")
    hyperedge_id = hyperedge_id.replace("*", "#")
    print(hyperedge_id)
    try:
        data = get_hyperedge_neighbor_server(hyperedge_id, database)
        return data
    except Exception as e:
        return {"error": str(e)}

class VertexModel(BaseModel):
    vertex_id: str
    entity_name: str = ""
    entity_type: str = ""
    description: str = ""
    additional_properties: str = ""
    database: str = None

class HyperedgeModel(BaseModel):
    vertices: list
    keywords: str = ""
    summary: str = ""
    database: str = None

class VertexUpdateModel(BaseModel):
    entity_name: str = ""
    entity_type: str = ""
    description: str = ""
    additional_properties: str = ""
    database: str = None

class HyperedgeUpdateModel(BaseModel):
    keywords: str = ""
    summary: str = ""
    database: str = None

@app.post("/db/vertices")
async def create_vertex(vertex: VertexModel):
    """
    创建新的vertex
    """
    try:
        result = add_vertex(vertex.vertex_id, {
            "entity_name": vertex.entity_name,
            "entity_type": vertex.entity_type,
            "description": vertex.description,
            "additional_properties": vertex.additional_properties
        }, vertex.database)
        return {"success": True, "message": "Vertex created successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/db/hyperedges")
async def create_hyperedge(hyperedge: HyperedgeModel):
    """
    创建新的hyperedge
    """
    try:
        result = add_hyperedge(hyperedge.vertices, {
            "keywords": hyperedge.keywords,
            "summary": hyperedge.summary
        }, hyperedge.database)
        return {"success": True, "message": "Hyperedge created successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/db/vertices/{vertex_id}")
async def update_vertex_endpoint(vertex_id: str, vertex: VertexUpdateModel):
    """
    更新vertex信息
    """
    try:
        vertex_id = vertex_id.replace("%20", " ")
        result = update_vertex(vertex_id, {
            "entity_name": vertex.entity_name,
            "entity_type": vertex.entity_type,
            "description": vertex.description,
            "additional_properties": vertex.additional_properties
        }, vertex.database)
        return {"success": True, "message": "Vertex updated successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.put("/db/hyperedges/{hyperedge_id}")
async def update_hyperedge_endpoint(hyperedge_id: str, hyperedge: HyperedgeUpdateModel):
    """
    更新hyperedge信息
    """
    try:
        hyperedge_id = hyperedge_id.replace("%20", " ")
        vertices = hyperedge_id.split("|*|")
        result = update_hyperedge(vertices, {
            "keywords": hyperedge.keywords,
            "summary": hyperedge.summary
        }, hyperedge.database)
        return {"success": True, "message": "Hyperedge updated successfully", "data": result}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/db/vertices/{vertex_id}")
async def delete_vertex_endpoint(vertex_id: str, database: str = None):
    """
    删除vertex
    """
    try:
        vertex_id = vertex_id.replace("%20", " ")
        result = delete_vertex(vertex_id, database)
        return {"success": True, "message": "Vertex deleted successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.delete("/db/hyperedges/{hyperedge_id}")
async def delete_hyperedge_endpoint(hyperedge_id: str, database: str = None):
    """
    删除hyperedge
    """
    try:
        hyperedge_id = hyperedge_id.replace("%20", " ")
        vertices = hyperedge_id.split("|*|")
        result = delete_hyperedge(vertices, database)
        return {"success": True, "message": "Hyperedge deleted successfully"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# 设置相关的API接口

class SettingsModel(BaseModel):
    apiKey: str = ""
    modelProvider: str = "openai"
    modelName: str = "gpt-5-mini"
    baseUrl: str = "https://api.openai.com/v1"
    selectedDatabase: str = ""
    maxTokens: int = 2000
    temperature: float = 0.7
    # HyperRAG 嵌入模型设置
    embeddingModel: str = "text-embedding-3-small"
    embeddingDim: int = 1536

class APITestModel(BaseModel):
    apiKey: str
    baseUrl: str
    modelName: str
    modelProvider: str

class DatabaseTestModel(BaseModel):
    database: str

@app.get("/settings")
async def get_settings():
    """
    获取系统设置
    """
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
            # 不返回敏感信息如API Key
            settings_safe = settings.copy()
            if 'apiKey' in settings_safe:
                settings_safe['apiKey'] = '***' if settings_safe['apiKey'] else ''
            return settings_safe
        else:
            # 返回默认设置
            return {
                "apiKey": "",
                "modelProvider": "openai",
                "modelName": "gpt-4o-mini",
                "baseUrl": "https://api.openai.com/v1",
                "selectedDatabase": "",
                "maxTokens": 2000,
                "temperature": 0.7,
                "embeddingModel": "text-embedding-3-small",
                "embeddingDim": 1536
            }
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/settings")
async def save_settings(settings: SettingsModel):
    """
    保存系统设置
    """
    try:
        settings_dict = settings.dict()
        
        # 如果apiKey是***，则保持原有的apiKey不变
        if settings_dict.get('apiKey') == '***':
            # 读取现有设置中的apiKey
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    existing_settings = json.load(f)
                # 保持原有的apiKey
                settings_dict['apiKey'] = existing_settings.get('apiKey', '')
            else:
                # 如果没有现有设置文件，则设为空字符串
                settings_dict['apiKey'] = ''
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=2)
        return {"success": True, "message": "设置保存成功"}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.get("/databases")
async def get_databases():
    """
    获取可用数据库列表
    """
    try:
        databases = []
        
        # 使用db_manager获取数据库列表
        database_files = db_manager.list_databases()
        
        for file in database_files:
            # 根据文件名推断描述
            description = f"{file.replace('.hgdb', '')}超图"
            
            databases.append({
                "name": file,
                "description": description
            })
        
        # 如果没有找到数据库文件，返回默认列表
        if not databases:
            databases = []
        
        return databases
    except Exception as e:
        return {"success": False, "message": str(e), "data": []}

@app.post("/test-api")
async def test_api_connection(api_test: APITestModel):
    """
    测试API连接
    """
    try:
        from openai import OpenAI
        
        # 根据不同的模型提供商进行测试
        if api_test.modelProvider == "openai":
            client = OpenAI(
                api_key=api_test.apiKey,
                base_url=api_test.baseUrl
            )
            
            # 发送一个简单的测试请求
            response = client.chat.completions.create(
                model=api_test.modelName,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            
            return {"success": True, "message": "API连接测试成功"}
            
        elif api_test.modelProvider == "anthropic":
            # 对于Anthropic，可以添加相应的测试逻辑
            return {"success": True, "message": "Anthropic API连接测试成功"}
            
        else:
            # 对于其他提供商，进行通用测试
            return {"success": True, "message": "API连接测试成功"}
            
    except Exception as e:
        return {"success": False, "message": f"API连接测试失败: {str(e)}"}

@app.post("/test-database")
async def test_database_connection(db_test: DatabaseTestModel):
    """
    测试数据库连接
    """
    try:
        # 使用db_manager测试数据库连接
        db = db_manager.get_database(db_test.database)
        
        # 尝试获取数据库的基本信息来验证连接
        vertices_count = len(db.all_v)
        edges_count = len(db.all_e)
        
        return {
            "success": True, 
            "message": "数据库连接测试成功",
            "info": {
                "vertices_count": vertices_count,
                "edges_count": edges_count,
                "database": db_test.database
            }
        }
        
    except Exception as e:
        return {"success": False, "message": f"数据库连接测试失败: {str(e)}"}


# 全局 HyperRAG 实例 - 改为字典来支持多数据库
hyperrag_instances = {}
hyperrag_working_dir = "hyperrag_cache"

async def get_hyperrag_llm_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
    """
    HyperRAG 专用的 LLM 函数，使用异步版本
    """
    try:
        main_logger.info(f"开始LLM调用，prompt长度: {len(prompt)} 字符")
        if system_prompt:
            main_logger.info(f"系统提示词长度: {len(system_prompt)} 字符")
        
        # 从设置文件读取配置
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        model_name = settings.get("modelName", "gpt-5-mini")
        api_key = settings.get("apiKey")
        base_url = settings.get("baseUrl")
        
        main_logger.info(f"使用模型: {model_name}, API地址: {base_url}")
        
        response = await openai_complete_if_cache(
            model_name,
            prompt,
            system_prompt=system_prompt,
            history_messages=history_messages,
            api_key=api_key,
            base_url=base_url,
            **kwargs,
        )
        
        main_logger.info(f"LLM调用完成，响应长度: {len(response)} 字符")
        return response
        
    except Exception as e:
        main_logger.error(f"LLM调用失败: {str(e)}")
        raise

async def get_hyperrag_embedding_func(texts: list[str]) -> np.ndarray:
    """
    HyperRAG 专用的嵌入函数
    """
    try:
        main_logger.info(f"开始文本嵌入，文本数量: {len(texts)}")
        main_logger.info(f"文本总长度: {sum(len(text) for text in texts)} 字符")
        
        # 从设置文件读取配置
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings = json.load(f)
        
        embedding_model = settings.get("embeddingModel", "text-embedding-3-small")
        api_key = settings.get("apiKey")
        base_url = settings.get("baseUrl")
        
        main_logger.info(f"使用嵌入模型: {embedding_model}")
        
        embeddings = await openai_embedding(
            texts,
            model=embedding_model,
            api_key=api_key,
            base_url=base_url,
        )
        
        main_logger.info(f"文本嵌入完成，嵌入维度: {embeddings.shape}")
        return embeddings
        
    except Exception as e:
        main_logger.error(f"文本嵌入失败: {str(e)}")
        raise

def get_or_create_hyperrag(database: str = None):
    """
    获取或创建指定数据库的 HyperRAG 实例
    """
    global hyperrag_instances
    
    if not HYPERRAG_AVAILABLE:
        main_logger.error("HyperRAG 不可用")
        raise RuntimeError("HyperRAG is not available")
    
    # 如果没有指定数据库，使用默认数据库
    if database is None:
        database = db_manager.default_database
        main_logger.info(f"使用默认数据库: {database}")
    
    # 检查是否已存在该数据库的实例
    if database not in hyperrag_instances:
        main_logger.info(f"创建新的HyperRAG实例，数据库: {database}")
        
        # 使用数据库名作为工作目录（去掉.hgdb后缀）
        if database.endswith('.hgdb'):
            db_dir_name = database.replace('.hgdb', '')
        else:
            db_dir_name = database
            
        # HyperRAG 工作目录直接使用 hyperrag_cache 下的数据库文件夹
        db_working_dir = os.path.join(hyperrag_working_dir, db_dir_name)
        Path(db_working_dir).mkdir(parents=True, exist_ok=True)
        
        main_logger.info(f"HyperRAG工作目录: {db_working_dir}")
        
        # 初始化 HyperRAG 实例
        hyperrag_instances[database] = HyperRAG(
            working_dir=db_working_dir,
            llm_model_func=get_hyperrag_llm_func,
            embedding_func=EmbeddingFunc(
                embedding_dim=1536,  # text-embedding-3-small 的维度
                max_token_size=8192,
                func=get_hyperrag_embedding_func
            ),
        )
        
        main_logger.info(f"HyperRAG实例创建完成，数据库: {database}")
    else:
        main_logger.info(f"使用现有HyperRAG实例，数据库: {database}")
    
    return hyperrag_instances[database]


class Message(BaseModel):
    message: str

@app.post("/process_message")
async def process_message(msg: Message):
    user_message = msg.message
    try:
        response_message = await get_hyperrag_llm_func(prompt=user_message)
    except Exception as e:
        return {"response": str(e)} 
    return {"response": response_message}

# HyperRAG 问答相关接口

class DocumentModel(BaseModel):
    content: str
    retries: int = 3
    database: str = None  # 添加数据库参数

class QueryModel(BaseModel):
    question: str
    mode: str = "hyper"  # hyper, hyper-lite, naive
    top_k: int = 60
    max_token_for_text_unit: int = 1600
    max_token_for_entity_context: int = 300
    max_token_for_relation_context: int = 1600
    only_need_context: bool = False
    response_type: str = "Multiple Paragraphs"
    database: str = None  # 添加数据库参数

@app.post("/hyperrag/insert")
async def insert_document(doc: DocumentModel):
    """
    向指定数据库的 HyperRAG 插入文档
    """
    if not HYPERRAG_AVAILABLE:
        return {"success": False, "message": "HyperRAG is not available"}
    
    try:
        rag = get_or_create_hyperrag(doc.database)
        
        # 重试机制
        for attempt in range(doc.retries):
            try:
                await rag.ainsert(doc.content)
                return {
                    "success": True, 
                    "message": "Document inserted successfully",
                    "database": doc.database or "default"
                }
            except Exception as e:
                if attempt == doc.retries - 1:
                    raise e
                print(f"Insert attempt {attempt + 1} failed: {e}. Retrying...")
                await asyncio.sleep(2)
                
    except Exception as e:
        return {"success": False, "message": f"Failed to insert document: {str(e)}"}

@app.post("/hyperrag/query")
async def query_hyperrag(query: QueryModel):
    """
    使用指定数据库的 HyperRAG 进行问答查询
    """
    if not HYPERRAG_AVAILABLE:
        return {"success": False, "message": "HyperRAG is not available"}
    
    try:
        rag = get_or_create_hyperrag(query.database)
        
        # 创建查询参数
        param = QueryParam(
            mode=query.mode,
            top_k=query.top_k,
            max_token_for_text_unit=query.max_token_for_text_unit,
            max_token_for_entity_context=query.max_token_for_entity_context,
            max_token_for_relation_context=query.max_token_for_relation_context,
            only_need_context=query.only_need_context,
            response_type=query.response_type,
            return_type='json'
        )
        
        # 执行查询
        result = await rag.aquery(query.question, param)
        
        # 处理结果格式
        return {
            "success": True,
            "response": result.get("response", ""),
            "entities": result.get("entities", []),
            "hyperedges": result.get("hyperedges", []),
            "text_units": result.get("text_units", []),
            "mode": query.mode,
            "question": query.question,
            "database": query.database or "default"
        }
        
    except Exception as e:
        return {"success": False, "message": f"Query failed: {str(e)}"}

@app.get("/hyperrag/status")
async def get_hyperrag_status(database: str = None):
    """
    获取指定数据库的 HyperRAG 实例状态
    """
    try:
        status = {
            "available": HYPERRAG_AVAILABLE,
            "database": database or "default",
            "working_dir": hyperrag_working_dir,
            "instances": list(hyperrag_instances.keys())
        }
        
        if database:
            # 获取特定数据库的状态
            if database in hyperrag_instances:
                instance = hyperrag_instances[database]
                status["initialized"] = True
                try:
                    status["details"] = {
                        "chunk_token_size": instance.chunk_token_size,
                        "llm_model_name": instance.llm_model_name,
                        "embedding_func_available": instance.embedding_func is not None,
                        "working_dir": os.path.join(hyperrag_working_dir, database.replace('.hgdb', ''))
                    }
                except Exception as e:
                    status["details"] = f"Error getting details: {str(e)}"
            else:
                status["initialized"] = False
        else:
            # 获取所有实例的概览
            status["initialized"] = len(hyperrag_instances) > 0
            status["total_instances"] = len(hyperrag_instances)
        
        return status
        
    except Exception as e:
        return {"success": False, "message": f"Failed to get status: {str(e)}"}

@app.delete("/hyperrag/reset")
async def reset_hyperrag(database: str = None):
    """
    重置指定数据库的 HyperRAG 实例，或重置所有实例
    """
    global hyperrag_instances
    
    try:
        if database:
            # 重置特定数据库的实例
            if database in hyperrag_instances:
                del hyperrag_instances[database]
                return {
                    "success": True, 
                    "message": f"HyperRAG instance for database '{database}' reset successfully"
                }
            else:
                return {
                    "success": False, 
                    "message": f"No HyperRAG instance found for database '{database}'"
                }
        else:
            # 重置所有实例
            hyperrag_instances = {}
            return {"success": True, "message": "All HyperRAG instances reset successfully"}
            
    except Exception as e:
        return {"success": False, "message": f"Failed to reset: {str(e)}"}

# 文件管理相关的API接口

class FileEmbedRequest(BaseModel):
    file_ids: List[str]
    chunk_size: int = 1000
    chunk_overlap: int = 200

@app.get("/files")
async def get_files():
    """
    获取所有上传的文件列表
    """
    try:
        files = file_manager.get_all_files()
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@app.post("/files/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    上传文件接口
    """
    print(f"\n{'='*50}")
    print(f"开始文件上传，文件数量: {len(files)}")
    print(f"{'='*50}")
    
    results = []
    
    for i, file in enumerate(files):
        try:
            print(f"\n上传文件 {i+1}/{len(files)}: {file.filename}")
            print(f"文件大小: {file.size if hasattr(file, 'size') else '未知'} bytes")
            
            # 读取文件内容
            print("正在读取文件内容...")
            content = await file.read()
            print(f"✅ 文件内容读取完成，实际大小: {len(content)} bytes")
            
            # 保存文件
            print("正在保存文件到本地...")
            file_info = await file_manager.save_uploaded_file(content, file.filename)
            file_info["status"] = "uploaded"
            print(f"✅ 文件保存成功: {file_info['filename']}")
            print(f"  - 文件ID: {file_info['file_id']}")
            print(f"  - 保存路径: {file_info['file_path']}")
            print(f"  - 数据库: {file_info['database_name']}")
            
            results.append(file_info)
            
        except Exception as e:
            error_msg = f"文件上传失败: {file.filename}, 错误: {str(e)}"
            print(f"❌ {error_msg}")
            main_logger.error(error_msg)
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    print(f"\n文件上传完成，成功: {len([r for r in results if r.get('status') == 'uploaded'])}/{len(files)}")
    print(f"{'='*50}")
    
    return {"files": results}

@app.delete("/files/{file_id}")
async def delete_file(file_id: str):
    """
    删除指定的文件
    """
    try:
        success = file_manager.delete_file(file_id)
        if success:
            return {"success": True, "message": "文件删除成功"}
        else:
            raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")

@app.post("/files/embed")
async def embed_files(request: FileEmbedRequest):
    """
    批量嵌入文档到HyperRAG
    """
    if not HYPERRAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="HyperRAG is not available")
    
    print(f"\n{'='*50}")
    print(f"开始文档嵌入，文件数量: {len(request.file_ids)}")
    print(f"配置参数: chunk_size={request.chunk_size}, chunk_overlap={request.chunk_overlap}")
    print(f"{'='*50}")
    
    results = []
    
    try:
        for i, file_id in enumerate(request.file_ids):
            try:
                print(f"\n处理文件 {i+1}/{len(request.file_ids)}: {file_id}")
                
                # 更新文件状态为处理中
                print("更新文件状态为处理中...")
                file_manager.update_file_status(file_id, "processing")
                
                # 获取文件信息
                print("获取文件信息...")
                file_info = file_manager.get_file_by_id(file_id)
                if not file_info:
                    error_msg = f"文件不存在: {file_id}"
                    print(f"❌ {error_msg}")
                    results.append({
                        "file_id": file_id,
                        "status": "error",
                        "error": "文件不存在"
                    })
                    continue
                
                print(f"✅ 文件信息: {file_info['filename']} ({file_info['file_size']} bytes)")
                
                # 使用文件对应的数据库名
                database_name = file_info["database_name"]
                print(f"目标数据库: {database_name}")
                rag = get_or_create_hyperrag(database_name)
                
                # 读取文件内容
                print("读取文件内容...")
                content = await file_manager.read_file_content(file_info["file_path"])
                print(f"✅ 内容长度: {len(content)} 字符")
                
                # 插入到HyperRAG
                print("开始文档嵌入...")
                await rag.ainsert(content)
                print("✅ 文档嵌入完成")
                
                # 更新文件状态为已嵌入
                file_manager.update_file_status(file_id, "embedded")
                
                results.append({
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "database_name": database_name,
                    "status": "embedded"
                })
                
                print(f"✅ 文件 {file_info['filename']} 嵌入成功")
                
            except Exception as e:
                # 更新文件状态为错误
                error_msg = f"文件嵌入失败: {file_id}, 错误: {str(e)}"
                print(f"❌ {error_msg}")
                file_manager.update_file_status(file_id, "error", str(e))
                
                results.append({
                    "file_id": file_id,
                    "status": "error",
                    "error": str(e)
                })
        
        successful = len([r for r in results if r.get('status') == 'embedded'])
        print(f"\n文档嵌入完成，成功: {successful}/{len(request.file_ids)}")
        print(f"{'='*50}")
        
        return {"embedded_files": results}
        
    except Exception as e:
        error_msg = f"批量嵌入失败: {str(e)}"
        print(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

# 自定义日志处理器，将日志通过WebSocket发送
class WebSocketLogHandler(logging.Handler):
    def __init__(self, connection_manager):
        super().__init__()
        self.connection_manager = connection_manager
        
    def emit(self, record):
        try:
            log_message = self.format(record)
            # 异步发送日志消息
            asyncio.create_task(self.connection_manager.send_log_message({
                "type": "log",
                "level": record.levelname,
                "message": log_message,
                "timestamp": record.created,
                "logger_name": record.name
            }))
        except Exception:
            pass  # 避免日志处理器自身错误影响主程序

# 自定义流处理器，捕获print语句和其他输出
class WebSocketStreamHandler:
    def __init__(self, connection_manager, stream_type="stdout"):
        self.connection_manager = connection_manager
        self.stream_type = stream_type
        self.original_stream = sys.stdout if stream_type == "stdout" else sys.stderr
        
    def write(self, message):
        # 同时写入原始流
        self.original_stream.write(message)
        self.original_stream.flush()
        
        # 发送到WebSocket（去除空行）
        if message.strip():
            asyncio.create_task(self.connection_manager.send_log_message({
                "type": "console",
                "level": "ERROR" if self.stream_type == "stderr" else "INFO",
                "message": message.strip(),
                "timestamp": asyncio.get_event_loop().time(),
                "source": self.stream_type
            }))
    
    def flush(self):
        self.original_stream.flush()

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.logging_enabled = False
        self.original_stdout = None
        self.original_stderr = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # 如果是第一个连接，启用日志重定向
        if len(self.active_connections) == 1 and not self.logging_enabled:
            self.enable_logging_redirect()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # 如果没有连接了，禁用日志重定向
        if len(self.active_connections) == 0 and self.logging_enabled:
            self.disable_logging_redirect()

    def enable_logging_redirect(self):
        """启用日志重定向"""
        if not self.logging_enabled:
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # 重定向标准输出和错误输出
            sys.stdout = WebSocketStreamHandler(self, "stdout")
            sys.stderr = WebSocketStreamHandler(self, "stderr")
            
            self.logging_enabled = True
            print("日志重定向已启用")

    def disable_logging_redirect(self):
        """禁用日志重定向"""
        if self.logging_enabled and self.original_stdout and self.original_stderr:
            sys.stdout = self.original_stdout
            sys.stderr = self.original_stderr
            self.logging_enabled = False
            print("日志重定向已禁用")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                # 如果连接已断开，标记为移除
                disconnected.append(connection)
        
        # 移除断开的连接
        for conn in disconnected:
            self.disconnect(conn)

    async def send_progress_update(self, progress_data: dict):
        """发送进度更新到所有连接的客户端"""
        message = json.dumps(progress_data)
        await self.broadcast(message)
    
    async def send_log_message(self, log_data: dict):
        """发送日志消息到所有连接的客户端"""
        message = json.dumps(log_data)
        await self.broadcast(message)

manager = ConnectionManager()

# 设置全面的日志配置
def setup_comprehensive_logging():
    """设置全面的日志配置"""
    # 设置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # 清除现有的处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 创建WebSocket处理器
    ws_handler = WebSocketLogHandler(manager)
    ws_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ws_handler.setFormatter(formatter)
    
    # 创建控制台处理器（保留控制台输出）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 添加处理器到根日志记录器
    root_logger.addHandler(ws_handler)
    root_logger.addHandler(console_handler)
    
    # 设置特定模块的日志级别
    logging.getLogger('hyperrag').setLevel(logging.INFO)
    logging.getLogger('openai').setLevel(logging.INFO)
    logging.getLogger('httpx').setLevel(logging.WARNING)  # 减少HTTP请求日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    # 确保HyperRAG相关的所有子模块都能输出日志
    hyperrag_modules = [
        'hyperrag.base',
        'hyperrag.hyperrag', 
        'hyperrag.llm',
        'hyperrag.operate',
        'hyperrag.prompt',
        'hyperrag.storage',
        'hyperrag.utils'
    ]
    
    for module_name in hyperrag_modules:
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(logging.INFO)
        # 确保模块日志也会传播到根记录器
        module_logger.propagate = True
    
    return root_logger

def configure_hyperrag_logging():
    """配置HyperRAG相关的详细日志输出"""
    try:
        # 如果HyperRAG可用，配置其内部日志
        if HYPERRAG_AVAILABLE:
            # 导入HyperRAG相关模块并设置日志
            try:
                import hyperrag
                import hyperrag.base
                import hyperrag.storage
                import hyperrag.llm
                import hyperrag.utils
                
                # 为HyperRAG的主要模块设置日志记录器
                modules_to_configure = [
                    hyperrag,
                    hyperrag.base,
                    hyperrag.storage, 
                    hyperrag.llm,
                    hyperrag.utils
                ]
                
                for module in modules_to_configure:
                    if hasattr(module, '__name__'):
                        logger = logging.getLogger(module.__name__)
                        logger.setLevel(logging.INFO)
                        logger.propagate = True
                        
                print("✅ HyperRAG日志配置完成")
                        
            except ImportError as e:
                print(f"⚠️  无法导入HyperRAG模块进行日志配置: {e}")
                
    except Exception as e:
        print(f"⚠️  HyperRAG日志配置失败: {e}")

# 初始化日志系统
main_logger = setup_comprehensive_logging()

# 配置HyperRAG日志
configure_hyperrag_logging()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # 这里可以处理客户端发送的消息
            await manager.send_personal_message(f"Message received: {data}", websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 带实时进度通知的文档嵌入接口
@app.post("/files/embed-with-progress")
async def embed_files_with_progress(request: FileEmbedRequest):
    """
    批量嵌入文档到HyperRAG，带实时进度通知
    """
    if not HYPERRAG_AVAILABLE:
        raise HTTPException(status_code=500, detail="HyperRAG is not available")
    
    # 立即返回处理开始的响应
    total_files = len(request.file_ids)
    
    # 异步处理文件嵌入
    asyncio.create_task(process_files_with_progress(request, total_files))
    
    return {
        "message": "文档嵌入处理已开始",
        "total_files": total_files,
        "processing": True
    }

async def process_files_with_progress(request: FileEmbedRequest, total_files: int):
    """异步处理文件嵌入并发送进度更新"""
    try:
        print(f"="*60)
        print(f"开始批量文件嵌入任务")
        print(f"文件总数: {total_files}")
        print(f"配置参数: chunk_size={request.chunk_size}, chunk_overlap={request.chunk_overlap}")
        print(f"="*60)
        
        main_logger.info(f"开始处理 {total_files} 个文件的嵌入任务")
        main_logger.info(f"配置参数: chunk_size={request.chunk_size}, chunk_overlap={request.chunk_overlap}")
        
        successful_files = 0
        failed_files = 0
        
        for i, file_id in enumerate(request.file_ids):
            try:
                print(f"\n{'='*40}")
                print(f"处理文件 {i + 1}/{total_files}")
                print(f"文件ID: {file_id}")
                print(f"{'='*40}")
                
                # 发送进度更新
                await manager.send_progress_update({
                    "type": "progress",
                    "file_id": file_id,
                    "current": i + 1,
                    "total": total_files,
                    "percentage": ((i + 1) / total_files) * 100,
                    "status": "processing",
                    "message": f"正在处理文件 {i + 1}/{total_files}"
                })
                
                # 更新文件状态为处理中
                print("更新文件状态为处理中...")
                file_manager.update_file_status(file_id, "processing")
                
                # 获取文件信息
                print("正在获取文件信息...")
                main_logger.info(f"获取文件信息: {file_id}")
                file_info = file_manager.get_file_by_id(file_id)
                if not file_info:
                    error_msg = f"文件不存在: {file_id}"
                    print(f"❌ 错误: {error_msg}")
                    main_logger.error(error_msg)
                    await manager.send_progress_update({
                        "type": "error",
                        "file_id": file_id,
                        "error": "文件不存在",
                        "current": i + 1,
                        "total": total_files
                    })
                    failed_files += 1
                    continue
                
                print(f"✅ 文件信息获取成功:")
                print(f"  - 文件名: {file_info['filename']}")
                print(f"  - 文件大小: {file_info['file_size']} bytes")
                print(f"  - 上传时间: {file_info['upload_time']}")
                
                # 使用文件对应的数据库名
                database_name = file_info["database_name"]
                print(f"  - 目标数据库: {database_name}")
                
                main_logger.info(f"开始处理文件: {file_info['filename']} ({file_info['file_size']} bytes)，使用数据库: {database_name}")
                
                # 为每个文件初始化对应的HyperRAG实例
                print("正在初始化 HyperRAG 实例...")
                main_logger.info(f"正在初始化 HyperRAG 实例，数据库: {database_name}")
                rag = get_or_create_hyperrag(database_name)
                print("✅ HyperRAG 实例初始化完成")
                main_logger.info(f"HyperRAG 实例初始化完成，使用数据库: {database_name}")
                
                # 发送详细进度信息
                await manager.send_progress_update({
                    "type": "file_processing",
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "database_name": database_name,
                    "stage": "reading",
                    "message": f"正在读取文件: {file_info['filename']} (数据库: {database_name})"
                })
                
                # 读取文件内容
                print("正在读取文件内容...")
                main_logger.info(f"开始读取文件内容: {file_info['filename']}")
                content = await file_manager.read_file_content(file_info["file_path"])
                print(f"✅ 文件读取完成，内容长度: {len(content)} 字符")
                main_logger.info(f"文件读取完成，内容长度: {len(content)} 字符")
                
                # 显示内容预览
                preview = content[:200] + "..." if len(content) > 200 else content
                print(f"内容预览: {preview}")
                
                # 发送嵌入阶段的进度
                await manager.send_progress_update({
                    "type": "file_processing",
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "database_name": database_name,
                    "stage": "embedding",
                    "message": f"正在嵌入文档: {file_info['filename']} (数据库: {database_name})"
                })
                
                # 插入到HyperRAG
                print("开始文档嵌入处理...")
                print("这个过程可能需要一些时间，请耐心等待...")
                main_logger.info(f"开始文档嵌入处理: {file_info['filename']}，数据库: {database_name}")
                main_logger.info("正在进行文档分块...")
                
                # 这里会触发HyperRAG的详细处理过程
                await rag.ainsert(content)
                
                print("✅ 文档嵌入完成！")
                main_logger.info(f"文档嵌入完成: {file_info['filename']}，数据库: {database_name}")
                
                # 更新文件状态为已嵌入
                file_manager.update_file_status(file_id, "embedded")
                
                # 发送成功完成的进度更新
                await manager.send_progress_update({
                    "type": "file_completed",
                    "file_id": file_id,
                    "filename": file_info["filename"],
                    "database_name": database_name,
                    "status": "completed",
                    "message": f"文件嵌入完成: {file_info['filename']} (数据库: {database_name})"
                })
                
                successful_files += 1
                print(f"✅ 文件 {file_info['filename']} 处理成功！")
                
            except Exception as e:
                # 更新文件状态为错误
                error_msg = f"文件处理失败: {file_id}, 错误: {str(e)}"
                print(f"❌ {error_msg}")
                main_logger.error(error_msg)
                file_manager.update_file_status(file_id, "error", str(e))
                
                # 发送错误进度更新
                await manager.send_progress_update({
                    "type": "file_error",
                    "file_id": file_id,
                    "error": str(e),
                    "current": i + 1,
                    "total": total_files
                })
                
                failed_files += 1
        
        # 发送整体完成的进度更新
        print(f"\n{'='*60}")
        print(f"批量文档处理完成！")
        print(f"总文件数: {total_files}")
        print(f"成功处理: {successful_files}")
        print(f"处理失败: {failed_files}")
        print(f"成功率: {(successful_files/total_files)*100:.1f}%")
        print(f"{'='*60}")
        
        main_logger.info(f"所有文档处理完成！总计: {total_files} 个文件，成功: {successful_files}，失败: {failed_files}")
        await manager.send_progress_update({
            "type": "all_completed",
            "message": f"所有文档处理完成 (成功: {successful_files}, 失败: {failed_files})",
            "total_files": total_files,
            "successful_files": successful_files,
            "failed_files": failed_files
        })
        
    except Exception as e:
        # 发送整体错误信息
        error_msg = f"批量嵌入失败: {str(e)}"
        print(f"❌ {error_msg}")
        main_logger.error(error_msg)
        await manager.send_progress_update({
            "type": "error",
            "error": error_msg
        })