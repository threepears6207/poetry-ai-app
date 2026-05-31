<script>
	export default {
		onLaunch: function() {
			console.log('App Launch')
			this.lockLandscape()
		},
		onShow: function() {
			console.log('App Show')
			this.lockLandscape()
		},
		onHide: function() {
			console.log('App Hide')
		},
		methods: {
			lockLandscape() {
				// #ifdef APP-PLUS
				try {
					if (typeof plus !== 'undefined' && plus.screen) {
						plus.screen.lockOrientation('landscape-primary')
					}
				} catch (e) {
					console.log('锁定横屏失败：', e)
				}
				// #endif
			}
		}
	}
</script>

<style>
	/*每个页面公共css */
</style>
