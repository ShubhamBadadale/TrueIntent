plugins { id("com.android.application"); id("org.jetbrains.kotlin.android") }
android {
    namespace = "org.trueintent.companion"
    compileSdk = 35
    defaultConfig { applicationId = "org.trueintent.companion"; minSdk = 26; targetSdk = 35; versionCode = 1; versionName = "0.1" }
    compileOptions { sourceCompatibility = JavaVersion.VERSION_17; targetCompatibility = JavaVersion.VERSION_17 }
    kotlinOptions { jvmTarget = "17" }
}
