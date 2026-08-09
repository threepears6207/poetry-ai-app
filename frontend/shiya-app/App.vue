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

						if (typeof plus !== 'undefined' && plus.navigator) {
							const enterImmersive = () => {
								plus.navigator.setFullscreen(true)
								if (typeof plus.navigator.hideSystemNavigation === 'function') {
									plus.navigator.hideSystemNavigation()
								}
							}

							enterImmersive()
							setTimeout(enterImmersive, 300)
						}
					} catch (e) {
						console.log('设置横屏沉浸模式失败：', e)
				}
				// #endif
			}
		}
	}
</script>

<style>
	@font-face {
		font-family: "ShiyaZhenKai";
		src: url("~@/static/fonts/LXGWZhenKaiGB-Regular.ttf") format("truetype");
		font-style: normal;
		font-weight: 400;
		font-display: swap;
	}

	/* 避免 App/H5 真机横屏缩放时根节点的默认白底露出一条边。 */
	html,
	body,
	#app,
	uni-app,
	uni-page,
	uni-page-wrapper,
	uni-page-body,
	page {
		width: 100%;
		height: 100%;
		margin: 0;
		padding: 0;
		overflow: hidden;
		background: #1a1a1a;
	}
</style>
