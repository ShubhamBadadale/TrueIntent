package org.trueintent.companion

import android.Manifest
import android.app.Activity
import android.os.Build
import android.os.Bundle
import android.content.pm.PackageManager
import android.telephony.PhoneStateListener
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import android.widget.*
import java.net.HttpURLConnection
import java.net.URL
import java.time.Instant
import java.util.UUID
import java.util.concurrent.Executors
import org.json.JSONObject

/** Course proof-of-concept, not trusted telemetry. No foreground service,
 * overlay/accessibility capture, attestation or mTLS. See ANDROID_COMPANION.md. */
@Suppress("DEPRECATION")
class MainActivity : Activity() {
    private lateinit var phone: TelephonyManager
    private var callback: TelephonyCallback? = null
    private var legacy: PhoneStateListener? = null
    private var active: Boolean? = null
    private lateinit var status: TextView
    private lateinit var output: TextView
    private lateinit var manual: CheckBox
    private lateinit var manualCall: CheckBox
    private lateinit var submit: Button
    private val worker = Executors.newSingleThreadExecutor()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        phone = getSystemService(TelephonyManager::class.java)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(28, 48, 28, 28) }
        fun label(value: String) = TextView(this).apply { text = value; layout.addView(this) }
        fun input(hintText: String, value: String) = EditText(this).apply { hint = hintText; setText(value); layout.addView(this) }
        label("TrueIntent - call signal demo")
        label("Sends one transaction check to your server. Call state is not evidence of fraud.")
        val server = input("Backend URL", "http://10.0.2.2:8000")
        val amount = input("Amount", "500")
        val velocity = input("Transactions in last hour", "1")
        status = label("Call state unknown")
        val permission = Button(this).apply { text = "Enable phone call signal"; layout.addView(this) }
        permission.setOnClickListener { requestPermissions(arrayOf(Manifest.permission.READ_PHONE_STATE), 1) }
        manual = CheckBox(this).apply { text = "Use manual demo input"; layout.addView(this) }
        manualCall = CheckBox(this).apply { text = "Manual: active call"; isEnabled = false; layout.addView(this) }
        manual.setOnCheckedChangeListener { _, checked -> manualCall.isEnabled = checked }
        submit = Button(this).apply { text = "Check transaction"; layout.addView(this) }
        output = label("")
        setContentView(ScrollView(this).apply { addView(layout) })
        submit.setOnClickListener {
            val money = amount.text.toString().toDoubleOrNull()
            val count = velocity.text.toString().toIntOrNull()
            if (money == null || !money.isFinite() || money <= 0 || count == null || count < 0) {
                output.text = "Enter a positive amount and non-negative transaction count."; return@setOnClickListener
            }
            if (!manual.isChecked && (active == null || checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED)) {
                output.text = "Call state unavailable. Enable permission and wait, or select manual demo input."; return@setOnClickListener
            }
            val prefs = getSharedPreferences("identity", MODE_PRIVATE)
            val id = prefs.getString("device_id", null) ?: UUID.randomUUID().toString().also { prefs.edit().putString("device_id", it).apply() }
            val now = Instant.now().toString()
            val payload = JSONObject().put("amount", money).put("transaction_velocity", count).put("device_id", id).put("timestamp", now)
            if (manual.isChecked) payload.put("is_active_call", manualCall.isChecked)
            else payload.put("call_telemetry", JSONObject().put("device_id", id).put("is_active_call", active).put("timestamp", now))
            val address = server.text.toString().trim().trimEnd('/') + "/check-transaction"
            submit.isEnabled = false
            output.text = "Checking..."
            worker.execute {
                var connection: HttpURLConnection? = null
                val result = try {
                    val url = URL(address)
                    require(url.protocol == "http" || url.protocol == "https") { "Use an HTTP(S) backend URL" }
                    connection = url.openConnection() as HttpURLConnection
                    connection!!.apply { requestMethod = "POST"; doOutput = true; instanceFollowRedirects = false; connectTimeout = 10000; readTimeout = 15000; setRequestProperty("Content-Type", "application/json") }
                    connection!!.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
                    val code = connection!!.responseCode
                    val stream = if (code in 200..299) connection!!.inputStream else connection!!.errorStream
                    val body = stream?.bufferedReader()?.use { it.readText() } ?: "No response body"
                    "HTTP $code: $body"
                } catch (error: Exception) { "Check failed: ${error.message}" }
                finally { connection?.disconnect() }
                runOnUiThread { if (!isDestroyed) { output.text = result; submit.isEnabled = true } }
            }
        }
    }

    private fun updateCall(state: Int) {
        // OFFHOOK includes dialing/active/held cellular calls; not arbitrary VoIP apps.
        active = state == TelephonyManager.CALL_STATE_OFFHOOK
        status.text = "Phone reports active call: $active"
    }

    private fun listen() {
        if (callback != null || legacy != null || checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) return
        try {
            if (Build.VERSION.SDK_INT >= 31) {
                val listener = object : TelephonyCallback(), TelephonyCallback.CallStateListener {
                    override fun onCallStateChanged(state: Int) { updateCall(state) }
                }
                phone.registerTelephonyCallback(mainExecutor, listener)
                callback = listener
            } else {
                val listener = object : PhoneStateListener() {
                    override fun onCallStateChanged(state: Int, number: String?) { updateCall(state) }
                }
                phone.listen(listener, PhoneStateListener.LISTEN_CALL_STATE)
                legacy = listener
            }
        } catch (error: Exception) { active = null; status.text = "Phone signal unavailable; manual demo is available." }
    }
    override fun onStart() { super.onStart(); listen() }
    override fun onStop() {
        try {
            if (Build.VERSION.SDK_INT >= 31) callback?.let { phone.unregisterTelephonyCallback(it) }
            legacy?.let { phone.listen(it, PhoneStateListener.LISTEN_NONE) }
        } catch (_: SecurityException) { /* Permission can be revoked while visible. */ }
        callback = null; legacy = null; active = null
        status.text = "Call state unknown"
        super.onStop()
    }
    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1) listen()
    }
    override fun onDestroy() { worker.shutdown(); super.onDestroy() }
}
