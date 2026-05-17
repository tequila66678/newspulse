package com.newspulse.app.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.newspulse.app.data.ApiService
import com.newspulse.app.data.NotificationResponse

@Composable
fun TrackingScreen(api: ApiService) {
    var notifications by remember { mutableStateOf<List<NotificationResponse>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }

    LaunchedEffect(Unit) {
        try {
            val resp = api.listNotifications(page = 1, pageSize = 50, type = "track")
            if (resp.isSuccessful) {
                notifications = resp.body()?.items ?: emptyList()
            }
        } catch (_: Exception) { }
        loading = false
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
            contentPadding = PaddingValues(16.dp)
        ) {
            items(notifications) { notif ->
                Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                    Column(Modifier.padding(12.dp)) {
                        notif.article?.let { article ->
                            Text(article.title, style = MaterialTheme.typography.titleSmall)
                            Text(article.source, style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }
    }
}
