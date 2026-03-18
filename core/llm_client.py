"""
大模型客户端 - 支持 Qwen API 和 Ollama/LM Studio
"""
import json
import httpx
from typing import Optional, Callable, AsyncGenerator
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """大模型客户端基类"""

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """生成回答"""
        pass

    @abstractmethod
    async def generate_stream(self, prompt: str, system_prompt: str = "", 
                              callback: Optional[Callable[[str], None]] = None) -> str:
        """流式生成回答"""
        pass


class QwenClient(BaseLLMClient):
    """通义千问 API 客户端"""

    def __init__(self, api_key: str, model: str = "qwen-max"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """同步生成回答"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {
                "max_tokens": 500,
                "temperature": 0.7
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            return result["output"]["text"]

    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None) -> str:
        """流式生成回答"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-DashScope-SSE": "enable"
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "input": {"messages": messages},
            "parameters": {
                "max_tokens": 500,
                "temperature": 0.7
            }
        }

        full_content = ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            content = chunk.get("output", {}).get("text", "")
                            if content:
                                full_content = content
                                if callback:
                                    callback(content)
                        except json.JSONDecodeError:
                            continue

        return full_content


class OllamaClient(BaseLLMClient):
    """Ollama 客户端"""

    def __init__(self, base_url: str, model: str = "qwen2.5:7b"):
        self.base_url = base_url.rstrip('/')
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """同步生成回答"""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "num_predict": 500,
                "temperature": 0.7
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            return result.get("response", "")

    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None) -> str:
        """流式生成回答"""
        url = f"{self.base_url}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt,
            "stream": True,
            "options": {
                "num_predict": 500,
                "temperature": 0.7
            }
        }

        full_content = ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    try:
                        chunk = json.loads(line)
                        content = chunk.get("response", "")
                        if content:
                            full_content += content
                            if callback:
                                callback(content)

                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue

        return full_content


class LMStudioClient(BaseLLMClient):
    """LM Studio 客户端 (使用 OpenAI 兼容 API)"""

    def __init__(self, base_url: str, model: str = "local-model"):
        self.base_url = base_url.rstrip('/')
        self.model = model

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        """同步生成回答"""
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Lower temperature for more focused responses
            "max_tokens": 500,
            "stream": False
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            # Extract content from OpenAI response format
            if "choices" in result and len(result["choices"]) > 0:
                message = result["choices"][0].get("message", {})
                content = message.get("content", "")
                # Extract just the answer part from Qwen3 thinking process format
                if content:
                    content = self._extract_answer_from_qwen3_content(content)
                return content
            return ""

    async def generate_stream(self, prompt: str, system_prompt: str = "",
                              callback: Optional[Callable[[str], None]] = None) -> str:
        """流式生成回答"""
        url = f"{self.base_url}/v1/chat/completions"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,  # Lower temperature for more focused responses
            "max_tokens": 500,
            "stream": True
        }

        full_content = ""

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.strip():
                        continue

                    # OpenAI streaming format: "data: {...}"
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]":
                            break

                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    # Extract just the answer part from Qwen3 thinking process format
                                    content = self._extract_answer_from_qwen3_content(content)
                                    full_content += content
                                    if callback:
                                        callback(content)
                        except json.JSONDecodeError:
                            continue

        return full_content

    def _extract_answer_from_qwen3_content(self, content: str) -> str:
        """Extract just the answer part from Qwen3 model's thinking process output"""
        if not content:
            return ""
        
        # Clean up the content first
        content = content.strip()
        
        # The Qwen3 model outputs thinking process in this format:
        # \Thinking Process:\n\n1. ...\n\n2. ...\n\n...\n\n\n\n<answer>
        # We need to extract everything after the last clear thinking process separator
        
        # Look for the pattern that separates thinking from answer
        # Based on observation, it's often multiple newlines or a clear delimiter
        
        # Method 1: Split by "\n\n\n\n" (4 newlines) which seems to be the separator
        if "\n\n\n\n" in content:
            parts = content.split("\n\n\n\n")
            # The answer should be in the last part
            answer_part = parts[-1].strip()
            if answer_part:
                return answer_part
        
        # Method 2: Look for the thinking process marker and take everything after it ends
        thinking_marker = "\Thinking Process:"
        if thinking_marker in content:
            # Find the end of the thinking process
            # Look for a pattern that indicates the thinking is done
            # Based on samples, it ends with a constructed response and then separator
            
            # Find the thinking process section
            thinking_start = content.find(thinking_marker)
            if thinking_start != -1:
                # Look for the end of thinking - look for common ending patterns
                # In the samples, it often ends with something like:
                # "6.  **Construct Response:** \"4\".\n\n\n\n\n4"
                # or similar pattern
                
                # Try to find where the actual answer starts after the thinking
                # Look for the last occurrence of a number or short answer at the end
                lines = content.split('\n')
                
                # Start from the end and look for the actual answer line
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    # Skip empty lines and lines that are clearly part of thinking
                    if not line:
                        continue
                    # Skip lines that contain thinking process markers
                    if any(marker in line.lower() for marker in [
                        'analyze', 'identify', 'execute', 'formulate', 'final', 
                        'check', 'construct', 'response:', 'decision:', 'option',
                        'draft:', 'refinement:', 'choice:', 'wait:', 'let:', 
                        'keep:', 'step:', 'phase:', 'stage:', 'review', 'safety',
                        'nuance', 'context', 'policy', 'violate'
                    ]):
                        continue
                    # If we find a line that looks like an answer (short, contains result)
                    # and it's not preceded by thinking markers on the same line
                    if len(line) < 20 and any(c.isdigit() for c in line):
                        # Additional check: make sure it's not part of a thinking step
                        if not any(prefix in line for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '10.']):
                            return line
                
                # Fallback: take everything after the last thinking-like line
                # Find where thinking process likely ends
                for i in range(len(lines) - 1, -1, -1):
                    line = lines[i].strip()
                    if line.endswith('".') or line.endswith("'.") or line.isdigit() or (len(line) < 10 and any(c.isdigit() for c in line)):
                        # Check if this looks like an answer line
                        if not any(marker in line.lower() for marker in [
                            'analyze', 'identify', 'execute', 'formulate', 'final', 
                            'check', 'construct', 'response:', 'decision:', 'option'
                        ]):
                            # Return this line and any following lines that look like continuation
                            answer_lines = []
                            for j in range(i, len(lines)):
                                answer_line = lines[j].strip()
                                if answer_line:
                                    # Stop if we hit another thinking marker
                                    if any(marker in answer_line.lower() for marker in [
                                        'analyze', 'identify', 'execute', 'formulate', 'final', 
                                        'check', 'construct', 'response:', 'decision:', 'option'
                                    ]) and j > i:  # Only stop if it's not the same line
                                        break
                                    answer_lines.append(answer_line)
                            return ' '.join(answer_lines).strip()
        
        # Method 3: Simple approach - take the last non-empty line that looks like an answer
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        if lines:
            # Check from the end for the answer
            for line in reversed(lines):
                # Skip obvious thinking process lines
                if any(skip in line.lower() for skip in [
                    'analyze', 'identify', 'execute', 'formulate', 'select', 'check', 
                    'final', 'option', 'draft', 'refinement', 'choice', 
                    'wait', 'let', 'keep', 'step', 'phase', 'stage',
                    'review', 'construct', 'response', 'decision', 'safety',
                    'nuance', 'context', 'policy', 'violate', 'trick'
                ]):
                    continue
                # If it's a short line that looks like an answer
                if len(line) < 50 and not line.startswith('*') and not line.startswith('-'):
                    # Clean up common answer prefixes
                    cleaned = line
                    for prefix in ['Answer:', 'The answer is:', 'Final Answer:', '答案：', '答案是：']:
                        if cleaned.startswith(prefix):
                            cleaned = cleaned[len(prefix):].strip()
                    # Remove quotes if they wrap the entire answer
                    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 2:
                        cleaned = cleaned[1:-1]
                    if cleaned.startswith("'") and cleaned.endswith("'") and len(cleaned) > 2:
                        cleaned = cleaned[1:-1]
                    if cleaned:
                        return cleaned
        
        # Fallback: return original content (shouldn't happen often)
        return content


class LLMClient:
    """统一大模型客户端 - 根据配置自动选择后端"""

    def __init__(self, config):
        self.config = config
        self.client = self._create_client()
        self.llm_mode = self.config.llm_mode

    def _create_client(self) -> BaseLLMClient:
        """根据配置创建客户端"""
        mode = self.config.llm_mode

        if mode == "qwen":
            return QwenClient(
                api_key=self.config.qwen_api_key,
                model=self.config.qwen_model
            )
        elif mode == "ollama":
            return OllamaClient(
                base_url=self.config.ollama_url,
                model=self.config.ollama_model
            )
        elif mode == "lmstudio":
            return LMStudioClient(
                base_url=self.config.get("llm.lmstudio.base_url", "http://localhost:1234"),
                model=self.config.get("llm.lmstudio.model", "local-model")
            )
        else:
            raise ValueError(f"未知的大模型模式：{mode}")

    def build_system_prompt(self, resume_text: str = "") -> str:
        """
        构建系统提示词

        Args:
            resume_text: 简历文本

        Returns:
            系统提示词
        """
        base_prompt = """你是一名专业的面试辅助 AI。你的任务是帮助面试者生成简洁、精准的回答。

## 回答规则
1. **简短精炼**: 每个回答控制在 50-100 字，只列出关键点
2. **结构化**: 使用 1-3 个要点，每点一句话
3. **基于简历**: 回答要结合面试者的实际经历
4. **避免废话**: 不要使用"我认为"、"我觉得"等填充词
5. **量化成果**: 优先使用数字和具体成果

## 输出格式
直接输出回答内容，不要有任何前缀或解释。"""

        # For LM Studio, add instruction to suppress thinking process
        if self.llm_mode == "lmstudio":
            base_prompt += "\n\n请不要输出思考过程，只输出最终答案。"

        if resume_text:
            return f"""{base_prompt}

## 面试者简历信息
{resume_text}

请基于以上简历信息，为面试者生成回答。"""

        return base_prompt

    async def generate_answer(self, question: str, resume_data: Optional[dict] = None) -> str:
        """
        生成面试回答

        Args:
            question: 面试问题
            resume_data: 简历数据（可选）

        Returns:
            AI 生成的回答
        """
        from core.resume_parser import ResumeParser

        resume_text = ""
        if resume_data:
            parser = ResumeParser()
            resume_text = parser.format_for_prompt(resume_data)

        system_prompt = self.build_system_prompt(resume_text)

        # 简短回答的 Prompt 强化
        prompt = f"""请回答以下面试问题（50-100 字，只列关键点）：

问题：{question}

回答："""

        return await self.client.generate(prompt, system_prompt)

    async def generate_answer_stream(self, question: str,
                                     resume_data: Optional[dict] = None,
                                     callback: Optional[Callable[[str], None]] = None) -> str:
        """
        流式生成面试回答

        Args:
            question: 面试问题
            resume_data: 简历数据（可选）
            callback: 每收到一段文本的回调函数

        Returns:
            AI 生成的完整回答
        """
        from core.resume_parser import ResumeParser

        resume_text = ""
        if resume_data:
            parser = ResumeParser()
            resume_text = parser.format_for_prompt(resume_data)

        system_prompt = self.build_system_prompt(resume_text)

        prompt = f"""请回答以下面试问题（50-100 字，只列关键点）：

问题：{question}

回答："""

        return await self.client.generate_stream(prompt, system_prompt, callback)

    def switch_mode(self, mode: str):
        """
        切换大模型模式

        Args:
            mode: "qwen", "ollama", 或 "lmstudio"
        """
        self.config.set("llm.mode", mode)
        self.client = self._create_client()