import { JSDOM } from 'jsdom';
import fs from 'fs/promises';


export class AdvancedCrawler {
  // Private fields for encapsulation
  #baseUrl;
  #visited;
  #queue;
  #results;
  #config;
  #activeRequests;

  constructor(baseUrl, options = {}) {
    this.#baseUrl = baseUrl;
    this.#visited = new Set();
    this.#queue = [{ url: baseUrl, depth: 0 }];
    this.#results = [];
    this.#activeRequests = 0;
    
    // Default configuration with ES6 defaults
    this.#config = {
      maxPages: options.maxPages || 50,
      maxDepth: options.maxDepth || 3,
      concurrency: options.concurrency || 5,
      delay: options.delay || 100,
      urlPattern: options.urlPattern || null,
      ...options
    };
  }

  // Concurrency limiter using a queue and Promise resolution
  async #enqueueRequest(task) {
    while (this.#activeRequests >= this.#config.concurrency) {
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    
    this.#activeRequests++;
    try {
      return await task();
    } finally {
      this.#activeRequests--;
    }
  }

  #isValidUrl(url, depth) {
    if (this.#visited.has(url)) return false;
    if (depth > this.#config.maxDepth) return false;
    if (this.#config.urlPattern && !new URL(url).pathname.match(this.#config.urlPattern)) return false;
    return true;
  }

  async #fetchHtml(url) {
    try {
      const response = await fetch(url, { 
        signal: AbortSignal.timeout(5000),
        headers: { 'User-Agent': 'AdvancedCrawler/1.0' }
      });
      
      if (!response.ok) throw new Error(`Status ${response.status}`);
      return await response.text();
    } catch (error) {
      throw new Error(`Fetch failed for ${url}: ${error.message}`);
    }
  }

  #extractLinks(html, currentUrl) {
    const dom = new JSDOM(html);
    const links = new Set();
    const baseOrigin = new URL(this.#baseUrl).origin;

    dom.window.document.querySelectorAll('a[href]').forEach(a => {
      try {
        const fullUrl = new URL(a.getAttribute('href'), currentUrl).href;
        if (fullUrl.startsWith(baseOrigin)) {
          links.add(fullUrl);
        }
      } catch {
        // Ignore invalid URLs
      }
    });
    
    return links;
  }

  async #processPage(url, depth) {
    if (!this.#isValidUrl(url, depth)) return;

    this.#visited.add(url);
    console.log(`[Depth ${depth}] Crawling: ${url}`);

    try {
      const html = await this.#fetchHtml(url);
      const links = this.#extractLinks(html, url);
      const dom = new JSDOM(html);

      // Store result (example: storing first 100 chars)
      this.#results.push({ 
        url, 
        depth, 
        title: new JSDOM(html).window.document.title,
        snippet: dom.serialize()
      });

      

      // Add new links to queue
      for (const link of links) {
        if (!this.#visited.has(link)) {
          this.#queue.push({ url: link, depth: depth + 1 });
        }
      }
    } catch (error) {
      console.error(`Error processing ${url}: ${error.message}`);
    }
  }

  async crawl() {
    console.log(`Starting crawl from ${this.#baseUrl}...`);
    
    while (this.#queue.length > 0 && this.#visited.size < this.#config.maxPages) {
      const batch = this.#queue.splice(0, this.#config.concurrency);
      
      const promises = batch.map(({ url, depth }) => 
        this.#enqueueRequest(() => this.#processPage(url, depth))
      );

      await Promise.all(promises);
      
      // Rate limiting delay
      if (this.#queue.length > 0) {
        await new Promise(resolve => setTimeout(resolve, this.#config.delay));
      }
    }

    console.log(`Crawl finished. Visited ${this.#visited.size} pages.`);
    return this.#results;
  }
}

// Usage Example (ES Module)

const crawler = new AdvancedCrawler('https://learn.microsoft.com/en-us/windows/win32/api/', { 
  maxPages: 50, 
  maxDepth: 1, 
  concurrency: 3,
  // FIX: Match the actual path structure, or remove this line entirely to crawl all same-origin links
  urlPattern: /\/en-us\/windows\/win32\// 
});

try {
  console.log('Starting crawl...');
  const data = await crawler.crawl();
  await fs.writeFile(
    'crawl_results.json',
    JSON.stringify(data, null, 2),
    'utf-8'
  );

  console.log(`Visited ${data.length} pages.`);
  // console.log('Results:', data); // Uncomment to see data


} catch (err) {
  console.error('Crawl failed:', err);
}   