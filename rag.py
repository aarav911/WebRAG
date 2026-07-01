import chromadb
from chromadb.utils import embedding_functions
import ollama
import json

# Configuration
CHROMA_PERSIST_DIR = "./chroma_db"
COLLECTION_NAME = "win32_docs"
MODEL_NAME = "qwen2.5-coder:latest"
NUM_SUB_QUESTIONS = 3

class AdvancedRAGPipeline:
    def __init__(self):
        # Initialize ChromaDB Client
        self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collection = self.client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=self.embedding_func
        )
        
        # Ensure model is ready
        try:
            ollama.show(MODEL_NAME)
        except:
            print(f"Model {MODEL_NAME} not found. Pulling...")
            ollama.pull(MODEL_NAME)

    def generate_sub_questions(self, original_query: str) -> list:
        """
        Step 1: Ask LLM to generate diverse sub-questions to cover different aspects.
        """
        prompt = f"""
        You are a research assistant. Given the following main question, generate {NUM_SUB_QUESTIONS} 
        distinct, specific sub-questions that would help gather comprehensive information to answer it.
        Focus on different technical aspects (e.g., parameters, return values, usage examples, errors).
        
        Main Question: "{original_query}"
        
        Output ONLY the sub-questions, one per line, without numbering or bullets.
        """
        
        response = ollama.generate(model=MODEL_NAME, prompt=prompt)
        questions = [q.strip() for q in response['response'].split('\n') if q.strip()]
        
        # Always include the original query to ensure direct matches are found
        if original_query not in questions:
            questions.append(original_query)
            
        return questions

    def retrieve_context(self, queries: list, n_results_per_query: int = 3) -> dict:
        """
        Step 2: Retrieve documents for the original query AND all sub-questions.
        """
        all_documents = []
        all_metadatas = []
        seen_ids = set()
        
        print(f"Retrieving context for {len(queries)} queries...")
        
        for query in queries:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results_per_query,
                include=["documents", "metadatas"]
            )
            
            # Deduplicate results based on ID to avoid redundancy
            for i, doc in enumerate(results['documents'][0]):
                doc_id = results['ids'][0][i]
                if doc_id not in seen_ids:
                    all_documents.append(doc)
                    all_metadatas.append(results['metadatas'][0][i])
                    seen_ids.add(doc_id)
        
        return {
            "documents": all_documents,
            "metadatas": all_metadatas
        }

    def synthesize_answer(self, original_query: str, context_data: dict) -> str:
        """
        Step 3: Feed all gathered context to the LLM to write the final answer.
        """
        # Format context clearly
        context_text = ""
        for i, doc in enumerate(context_data['documents']):
            source = context_data['metadatas'][i].get('url', 'Unknown Source')
            context_text += f"[Source {i+1}: {source}]\n{doc}\n\n"
        
        prompt = f"""
        You are an expert technical writer. Answer the user's question using ONLY the provided context.
        Synthesize information from all sources to create a comprehensive, accurate, and well-structured answer.
        If the context contains code snippets or specific API parameters, include them.
        Cite your sources using [Source X] format where X is the source number.
        If the answer cannot be found in the context, state that clearly.

        Original Question: "{original_query}"

        Provided Context:
        {context_text}

        Original Question: "{original_query}"


        Comprehensive Answer:
        """
        
        response = ollama.generate(model=MODEL_NAME, prompt=prompt, options={"temperature": 0.3})
        return response['response']

    def query(self, user_question: str):
        """Main execution flow"""
        print(f"\n--- Processing: '{user_question}' ---\n")
        
        # 1. Expand Query
        sub_questions = self.generate_sub_questions(user_question)
        print(f"Generated Sub-Questions:\n" + "\n".join([f"- {q}" for q in sub_questions]) + "\n")
        
        # 2. Retrieve
        context = self.retrieve_context(sub_questions)
        print(f"Retrieved {len(context['documents'])} unique context chunks.\n")
        for c in context['documents']:
            print()
            print(c)

        
        if not context['documents']:
            return "No relevant information found in the database."
        
        # 3. Synthesize
        print("Synthesizing final answer...\n")
        final_answer = self.synthesize_answer(user_question, context)
        
        return final_answer

if __name__ == "__main__":
    pipeline = AdvancedRAGPipeline()
    
    # Example Query
    query = "How do i make a window, with a moving circle in it?"
    answer = pipeline.query(query)
    
    print("\n=== FINAL ANSWER ===\n")
    print(answer)   