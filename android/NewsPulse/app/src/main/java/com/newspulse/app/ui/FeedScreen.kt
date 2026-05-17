package com.newspulse.app.ui

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.newspulse.app.data.ApiService
import com.newspulse.app.data.ArticleResponse

@Composable
fun FeedScreen(api: ApiService) {
    var articles by remember { mutableStateOf<List<ArticleResponse>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        try {
            val resp = api.listArticles(page = 1, pageSize = 50)
            if (resp.isSuccessful) {
                articles = resp.body()?.items ?: emptyList()
            }
        } catch (_: Exception) { }
        loading = false
    }

    if (loading) {
        Box(Modifier.fillMaxSize()) {
            CircularProgressIndicator(Modifier.align(Alignment.Center))
        }
    } else {
        LazyColumn(
            modifier = Modifier.fillMaxSize(),
            contentPadding = PaddingValues(16.dp)
        ) {
            items(articles) { article ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).clickable { },
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text(article.title, style = MaterialTheme.typography.titleSmall)
                        article.summary?.let {
                            Text(
                                it,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 2,
                                modifier = Modifier.padding(top = 4.dp)
                            )
                        }
                        Row(
                            Modifier.fillMaxWidth().padding(top = 4.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(article.source, style = MaterialTheme.typography.labelSmall)
                            Text("热度: ${"%.1f".format(article.score)}", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }
    }
}
