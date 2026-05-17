package com.newspulse.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.newspulse.app.data.ApiService
import com.newspulse.app.data.NotificationResponse
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

@Composable
fun TrackingScreen(api: ApiService) {
    var notifications by remember { mutableStateOf<List<NotificationResponse>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    val scope = rememberCoroutineScope()

    suspend fun refresh() {
        try {
            val resp = api.listNotifications(page = 1, pageSize = 50, type = "track")
            if (resp.isSuccessful) {
                notifications = resp.body()?.items ?: emptyList()
            }
        } catch (_: Exception) { }
        loading = false
    }

    LaunchedEffect(Unit) {
        refresh()
        while (true) {
            delay(30_000)
            try {
                val resp = api.listNotifications(page = 1, pageSize = 50, type = "track")
                if (resp.isSuccessful) {
                    notifications = resp.body()?.items ?: emptyList()
                }
            } catch (_: Exception) { }
        }
    }

    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("消息追踪", style = MaterialTheme.typography.titleMedium)
            IconButton(onClick = { loading = true; scope.launch { refresh() } }) {
                Icon(Icons.Default.Refresh, contentDescription = "刷新")
            }
        }

        if (loading) {
            Box(Modifier.fillMaxSize()) {
                CircularProgressIndicator(Modifier.align(Alignment.Center))
            }
        } else if (notifications.isEmpty()) {
            Box(Modifier.fillMaxSize()) {
                Text("暂无追踪消息", Modifier.align(Alignment.Center))
            }
        } else {
            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp)
            ) {
                items(notifications) { notif ->
                    val bgColor = if (notif.read)
                        CardDefaults.cardColors().containerColor
                    else
                        MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f)

                    Card(
                        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                        colors = CardDefaults.cardColors(containerColor = bgColor)
                    ) {
                        Column(Modifier.padding(12.dp)) {
                            notif.article?.let { article ->
                                Text(article.title, style = MaterialTheme.typography.titleSmall)
                                Text(article.source, style = MaterialTheme.typography.labelSmall, modifier = Modifier.padding(top = 4.dp))
                            }
                            if (!notif.read) {
                                Text("新", style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(top = 4.dp))
                            }
                        }
                    }
                }
            }
        }
    }
}
