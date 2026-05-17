package com.newspulse.app

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.newspulse.app.data.AuthStore
import com.newspulse.app.data.FcmTokenUpdate
import com.newspulse.app.data.RetrofitClient
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class FcmService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        sendTokenToServer(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val title = message.notification?.title ?: "NewsPulse"
        val body = message.notification?.body ?: ""
        val type = message.data["type"] ?: "track"
        val articleId = message.data["article_id"]
        val digestId = message.data["digest_id"]

        showNotification(title, body, type, articleId, digestId)
    }

    private fun sendTokenToServer(token: String) {
        val authStore = AuthStore(this)
        val api = RetrofitClient.create(this)
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val serverToken = authStore.getToken()
                if (serverToken != null) {
                    api.updateFcmToken(FcmTokenUpdate(token))
                }
            } catch (_: Exception) { }
        }
    }

    private fun showNotification(title: String, body: String, type: String, articleId: String?, digestId: String?) {
        val channelId = "newspulse_channel"
        val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(channelId, "NewsPulse", NotificationManager.IMPORTANCE_HIGH)
            notificationManager.createNotificationChannel(channel)
        }

        val intent = Intent(this, MainActivity::class.java).apply {
            putExtra("type", type)
            articleId?.let { putExtra("article_id", it) }
            digestId?.let { putExtra("digest_id", it) }
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }

        val pendingIntent = PendingIntent.getActivity(
            this, System.currentTimeMillis().toInt(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setContentIntent(pendingIntent)
            .build()

        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }
}
